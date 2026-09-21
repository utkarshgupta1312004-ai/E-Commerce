import logging
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any, List

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import Avg, Count, Q

from .models import Review, ReviewMedia, ReviewReply, ReviewVote

logger = logging.getLogger(__name__)
User = get_user_model()


class ReviewService:
    """
    Centralized domain service managing reviews, ratings aggregation,
    purchase verification, moderation, and permissions.
    """

    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/jpg']
    MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

    @staticmethod
    def check_verified_purchase(user, product, variant=None) -> Tuple[bool, Optional[Any]]:
        """
        Determines server-side if customer actually purchased and received this product.
        Requirement 5 & 36: Verified Purchase must be calculated server-side.
        Returns (is_verified, order_item).
        """
        if not user or not getattr(user, 'is_authenticated', False):
            return False, None

        try:
            from apps.orders.models import OrderItem
            order_items_qs = OrderItem.objects.filter(
                order__user=user,
                product=product,
                order__status='DELIVERED'
            ).select_related('order').order_by('-order__created_at')

            if variant:
                variant_item = order_items_qs.filter(variant=variant).first()
                if variant_item:
                    return True, variant_item

            item = order_items_qs.first()
            if item:
                return True, item

            # If no DELIVERED order, check if any order has been completed/paid
            active_item = OrderItem.objects.filter(
                order__user=user,
                product=product,
                order__status__in=['SHIPPED', 'OUT_FOR_DELIVERY', 'CONFIRMED']
            ).order_by('-order__created_at').first()
            if active_item:
                # Purchased, but not yet delivered
                return False, active_item

            return False, None
        except Exception as e:
            logger.warning(f"Error checking verified purchase for user {user} and product {product}: {e}")
            return False, None

    @classmethod
    def update_product_rating_cache(cls, product) -> Tuple[Decimal, int]:
        """
        Requirement 16, 17, 29: Recalculates Product.rating and Product.review_count
        from actual approved Review records using database aggregation.
        Keeps Product Detail, Product Cards, and Catalog Filters 100% consistent.
        """
        approved_reviews = product.reviews.filter(status=Review.STATUS_APPROVED)
        stats = approved_reviews.aggregate(
            avg_rating=Avg('rating'),
            total_count=Count('id')
        )

        total_count = stats['total_count'] or 0
        raw_avg = stats['avg_rating']

        if total_count > 0 and raw_avg is not None:
            avg_decimal = Decimal(str(round(float(raw_avg), 2)))
        else:
            avg_decimal = Decimal('5.00')  # Default initial rating

        product.rating = avg_decimal
        product.review_count = total_count
        product.save(update_fields=['rating', 'review_count', 'updated_at'])

        return avg_decimal, total_count

    @classmethod
    def get_product_review_summary(cls, product) -> Dict[str, Any]:
        """
        Requirement 15 & 16: Computes product rating summary and distribution.
        5★, 4★, 3★, 2★, 1★ breakdown with counts and percentages.
        """
        approved_reviews = product.reviews.filter(status=Review.STATUS_APPROVED)
        total_count = approved_reviews.count()

        if total_count > 0:
            avg_rating = approved_reviews.aggregate(avg=Avg('rating'))['avg']
            avg_float = round(float(avg_rating or 5.0), 1)
        else:
            avg_float = 5.0

        # Distribution counts
        breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        counts_by_star = approved_reviews.values('rating').annotate(c=Count('id'))
        for item in counts_by_star:
            r = item['rating']
            if r in breakdown:
                breakdown[r] = item['c']

        distribution = []
        for star in [5, 4, 3, 2, 1]:
            count = breakdown[star]
            pct = round((count / total_count * 100)) if total_count > 0 else 0
            distribution.append({
                'star': star,
                'count': count,
                'percentage': pct,
            })

        # Average rating rounded for whole star icons
        full_stars = int(avg_float)
        has_half = (avg_float - full_stars) >= 0.4
        empty_stars = 5 - full_stars - (1 if has_half else 0)

        return {
            'total_reviews': total_count,
            'average_rating': avg_float,
            'distribution': distribution,
            'full_stars': range(full_stars),
            'has_half': has_half,
            'empty_stars': range(max(0, empty_stars)),
        }

    @classmethod
    def can_manage_reviews(cls, user, request=None) -> bool:
        """
        Requirement 13: Determines if user has authorized management/staff access
        to moderate reviews or create official seller responses.
        """
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser or user.is_staff:
            return True

        if hasattr(user, 'profile') and user.profile.is_management_staff:
            return True

        if request and request.session:
            dept = request.session.get('department_slug')
            if dept in ('catalog', 'support', 'orders'):
                return True

        return False

    @classmethod
    def submit_or_update_review(
        cls,
        user,
        product,
        rating: int,
        title: str,
        comment: str,
        variant=None,
        media_files: Optional[List[Any]] = None
    ) -> Tuple[Review, bool]:
        """
        Requirement 4, 6, 7, 8, 10: Authenticated customer submits or edits review.
        Enforces 1 review per customer per product.
        Validates rating (1..5) server-side and checks verified purchase.
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to submit a review.")

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValidationError("Rating must be an integer between 1 and 5.")
        except (ValueError, TypeError):
            raise ValidationError("Invalid rating value provided.")

        title = (title or "").strip()[:200]
        comment = (comment or "").strip()
        if not comment:
            raise ValidationError("Review comment cannot be empty.")

        is_verified, order_item = cls.check_verified_purchase(user, product, variant)

        with transaction.atomic():
            review, created = Review.objects.get_or_create(
                user=user,
                product=product,
                defaults={
                    'variant': variant,
                    'order_item': order_item,
                    'rating': rating,
                    'title': title,
                    'comment': comment,
                    'is_verified_purchase': is_verified,
                    'status': Review.STATUS_APPROVED,
                }
            )

            if not created:
                # Update existing review
                review.rating = rating
                review.title = title
                review.comment = comment
                if variant and not review.variant:
                    review.variant = variant
                if is_verified and not review.is_verified_purchase:
                    review.is_verified_purchase = True
                    review.order_item = order_item
                review.save()

            # Handle optional media uploads (Requirement 10)
            if media_files:
                for file_obj in media_files:
                    if file_obj and hasattr(file_obj, 'size'):
                        if file_obj.size > cls.MAX_IMAGE_SIZE_BYTES:
                            logger.warning(f"Skipping oversized review image {file_obj.name}")
                            continue
                        content_type = getattr(file_obj, 'content_type', '')
                        if content_type and content_type not in cls.ALLOWED_IMAGE_TYPES:
                            logger.warning(f"Skipping invalid image type {content_type}")
                            continue
                        ReviewMedia.objects.create(
                            review=review,
                            image=file_obj
                        )

            # Re-aggregate Product rating and count
            cls.update_product_rating_cache(product)

        return review, created

    @classmethod
    def delete_review(cls, user, review_id: int, request=None) -> bool:
        """
        Requirement 25: Deletes review securely.
        Only the review author or authorized management staff can delete.
        """
        try:
            review = Review.objects.select_related('product').get(id=review_id)
        except Review.DoesNotExist:
            return False

        is_owner = (review.user_id == user.id)
        is_staff = cls.can_manage_reviews(user, request)

        if not (is_owner or is_staff):
            raise PermissionDenied("You do not have permission to delete this review.")

        product = review.product
        with transaction.atomic():
            review.delete()
            cls.update_product_rating_cache(product)

        return True

    @classmethod
    def vote_helpful(cls, user, review_id: int) -> Tuple[bool, int]:
        """
        Requirement 26: Helpful review voting.
        Enforces 1 vote per customer per review.
        Returns (has_voted, current_helpful_count).
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to vote on reviews.")

        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            raise ValidationError("Review does not exist.")

        vote, created = ReviewVote.objects.get_or_create(
            review=review,
            user=user,
            defaults={'is_helpful': True}
        )

        if not created:
            # User already voted; toggle or remove vote
            vote.delete()
            if review.helpful_count > 0:
                review.helpful_count = max(0, review.helpful_count - 1)
                review.save(update_fields=['helpful_count'])
            return False, review.helpful_count
        else:
            review.helpful_count += 1
            review.save(update_fields=['helpful_count'])
            return True, review.helpful_count

    @classmethod
    def add_official_reply(cls, staff_user, review_id: int, reply_text: str, request=None) -> ReviewReply:
        """
        Requirement 11, 12, 13: Add or update official seller/admin reply.
        Staff only. Non-customers only.
        """
        if not cls.can_manage_reviews(staff_user, request):
            raise PermissionDenied("Only authorized store management can post official seller replies.")

        reply_text = (reply_text or "").strip()
        if not reply_text:
            raise ValidationError("Reply text cannot be empty.")

        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            raise ValidationError("Review does not exist.")

        reply = ReviewReply.objects.create(
            review=review,
            user=staff_user,
            reply_text=reply_text
        )

        return reply

    @classmethod
    def moderate_review(cls, staff_user, review_id: int, new_status: str, request=None) -> Review:
        """
        Requirement 19, 21: Staff changes moderation status (APPROVED, PENDING, REJECTED).
        Updates product rating cache immediately if visibility changes.
        """
        if not cls.can_manage_reviews(staff_user, request):
            raise PermissionDenied("Staff permission required to moderate reviews.")

        if new_status not in (Review.STATUS_APPROVED, Review.STATUS_PENDING, Review.STATUS_REJECTED):
            raise ValidationError("Invalid moderation status.")

        with transaction.atomic():
            review = Review.objects.select_related('product').get(id=review_id)
            review.status = new_status
            review.save(update_fields=['status', 'updated_at'])

            cls.update_product_rating_cache(review.product)

        return review
