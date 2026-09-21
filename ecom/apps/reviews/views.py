import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from apps.catalog.models import Product, ProductVariant
from .models import Review, ReviewReply
from .services import ReviewService


def _check_staff_access(request) -> bool:
    """Helper verifying management access for staff review views."""
    return ReviewService.can_manage_reviews(request.user, request)


# ==============================================================================
# 1. CUSTOMER STOREFRONT REVIEW ACTIONS
# ==============================================================================

@login_required(login_url='/accounts/login/')
@require_POST
def submit_review_view(request, slug):
    """
    Requirement 4, 6, 7, 35: Authenticated customer submits review for a product.
    Handles rating, title, comment, variant configuration, and optional image media.
    Redirects back to Product Detail page #reviews.
    """
    product = get_object_or_404(Product, slug=slug)

    rating = request.POST.get('rating')
    title = request.POST.get('title', '')
    comment = request.POST.get('comment', '')
    variant_id = request.POST.get('variant_id')

    variant = None
    if variant_id:
        try:
            variant = product.variants.filter(id=int(variant_id)).first()
        except (ValueError, TypeError):
            variant = None

    media_files = request.FILES.getlist('images')

    try:
        review, created = ReviewService.submit_or_update_review(
            user=request.user,
            product=product,
            rating=rating,
            title=title,
            comment=comment,
            variant=variant,
            media_files=media_files
        )

        if created:
            messages.success(request, "🎉 Your review has been submitted and published successfully!")
        else:
            messages.success(request, "✏️ Your review has been successfully updated!")
    except ValidationError as e:
        messages.error(request, f"Review error: {e}")
    except PermissionDenied as e:
        messages.error(request, f"Permission error: {e}")
    except Exception as e:
        messages.error(request, f"An unexpected error occurred: {e}")

    return redirect(f"{product.get_absolute_url()}#reviews")


@login_required(login_url='/accounts/login/')
@require_POST
def edit_review_view(request, review_id):
    """
    Requirement 24: Customer edits their own review.
    Cannot edit another user's review.
    """
    review = get_object_or_404(Review, id=review_id)
    if review.user != request.user and not _check_staff_access(request):
        raise PermissionDenied("You can only edit your own review.")

    rating = request.POST.get('rating')
    title = request.POST.get('title', '')
    comment = request.POST.get('comment', '')

    try:
        ReviewService.submit_or_update_review(
            user=review.user,
            product=review.product,
            rating=rating,
            title=title,
            comment=comment,
            variant=review.variant
        )
        messages.success(request, "Your review has been updated.")
    except Exception as e:
        messages.error(request, f"Error updating review: {e}")

    return redirect(f"{review.product.get_absolute_url()}#reviews")


@login_required(login_url='/accounts/login/')
@require_POST
def delete_review_view(request, review_id):
    """
    Requirement 25: Customer deletes only their own review via POST.
    Management staff can delete reviews according to permissions.
    """
    try:
        review = Review.objects.select_related('product').get(id=review_id)
        product_url = review.product.get_absolute_url()
        ReviewService.delete_review(request.user, review_id, request)
        messages.success(request, "Review was successfully removed.")
        return redirect(f"{product_url}#reviews")
    except Review.DoesNotExist:
        messages.error(request, "Review not found.")
        return redirect('catalog:product_list')
    except PermissionDenied:
        messages.error(request, "You do not have permission to delete this review.")
        return redirect('catalog:product_list')


@login_required(login_url='/accounts/login/')
@require_POST
def vote_helpful_view(request, review_id):
    """
    Requirement 26: Helpful review voting with toggle.
    Supports standard form POST or asynchronous JSON fetch requests.
    """
    try:
        has_voted, current_count = ReviewService.vote_helpful(request.user, review_id)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({
                'success': True,
                'has_voted': has_voted,
                'helpful_count': current_count
            })
        messages.success(request, "Thank you for your feedback!")
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        messages.error(request, str(e))

    # Fallback redirect to referrer or product
    next_url = request.META.get('HTTP_REFERER', '/')
    return redirect(next_url)


# ==============================================================================
# 2. MANAGEMENT CONSOLE REVIEW ACTIONS & VIEWS
# ==============================================================================

@login_required(login_url='/management/login/')
@require_POST
def reply_review_view(request, review_id):
    """
    Requirement 11, 12, 13: Authorized management user creates an official seller reply.
    """
    if not _check_staff_access(request):
        messages.error(request, "Only authorized management users can reply to customer reviews.")
        return redirect('management:portal')

    reply_text = request.POST.get('reply_text', '').strip()
    try:
        review = get_object_or_404(Review.objects.select_related('product'), id=review_id)
        ReviewService.add_official_reply(request.user, review_id, reply_text, request)
        messages.success(request, f"Official reply posted for {review.author_display_name}'s review.")
    except Exception as e:
        messages.error(request, f"Failed to post reply: {e}")

    next_url = request.META.get('HTTP_REFERER') or f"{review.product.get_absolute_url()}#reviews"
    return redirect(next_url)


@login_required(login_url='/management/login/')
@require_POST
def moderate_review_view(request, review_id):
    """
    Requirement 19, 21: Staff changes moderation status (APPROVED, REJECTED, PENDING).
    """
    if not _check_staff_access(request):
        messages.error(request, "Unauthorized moderation request.")
        return redirect('management:portal')

    new_status = request.POST.get('status')
    try:
        ReviewService.moderate_review(request.user, review_id, new_status, request)
        messages.success(request, f"Review #{review_id} status updated to {new_status}.")
    except Exception as e:
        messages.error(request, f"Moderation failed: {e}")

    next_url = request.META.get('HTTP_REFERER') or 'catalog:product_admin_list'
    return redirect(next_url)


def product_reviews_manage_view(request, product_id):
    """
    Requirement 22 & 41: Product-Specific Review Management.
    Shows Product, Average Rating, Total Reviews, and all reviews for that product.
    Allows Approve, Reject, Reply, and Moderate.
    """
    if not _check_staff_access(request):
        messages.error(request, "Access restricted to Catalog Staff and Super Administrators.")
        return redirect('management:portal')

    product = get_object_or_404(Product, id=product_id)
    summary = ReviewService.get_product_review_summary(product)

    reviews_qs = product.reviews.select_related('user', 'variant').prefetch_related('replies__user', 'media').order_by('-created_at')

    status_filter = request.GET.get('status', '').strip()
    if status_filter in (Review.STATUS_APPROVED, Review.STATUS_PENDING, Review.STATUS_REJECTED):
        reviews_qs = reviews_qs.filter(status=status_filter)

    rating_filter = request.GET.get('rating', '').strip()
    if rating_filter.isdigit():
        reviews_qs = reviews_qs.filter(rating=int(rating_filter))

    paginator = Paginator(reviews_qs, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    from apps.catalog.views import _get_catalog_staff_context
    context = _get_catalog_staff_context(request, active_tab='reviews')
    context.update({
        'product': product,
        'summary': summary,
        'page_obj': page_obj,
        'reviews': page_obj.object_list,
        'total_count': paginator.count,
        'status_filter': status_filter,
        'rating_filter': rating_filter,
    })
    return render(request, 'reviews/manage_product_reviews.html', context)


def catalog_reviews_manage_view(request):
    """
    Requirement 21: Overall Catalog Reviews Management Console.
    Allows filtering by product, rating, status, search customer/text, and moderating/replying.
    """
    if not _check_staff_access(request):
        messages.error(request, "Access restricted to Catalog Staff and Super Administrators.")
        return redirect('management:portal')

    queryset = Review.objects.select_related('product', 'user', 'variant').prefetch_related('replies__user', 'media').order_by('-created_at')

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    rating_filter = request.GET.get('rating', '').strip()
    verified_only = request.GET.get('verified', '').strip()

    if q:
        queryset = queryset.filter(
            Q(product__title__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__first_name__icontains=q) |
            Q(title__icontains=q) |
            Q(comment__icontains=q)
        ).distinct()

    if status_filter in (Review.STATUS_APPROVED, Review.STATUS_PENDING, Review.STATUS_REJECTED):
        queryset = queryset.filter(status=status_filter)

    if rating_filter.isdigit():
        queryset = queryset.filter(rating=int(rating_filter))

    if verified_only == '1':
        queryset = queryset.filter(is_verified_purchase=True)

    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Global KPI counts
    total_reviews = Review.objects.count()
    pending_count = Review.objects.filter(status=Review.STATUS_PENDING).count()
    approved_count = Review.objects.filter(status=Review.STATUS_APPROVED).count()
    rejected_count = Review.objects.filter(status=Review.STATUS_REJECTED).count()

    from apps.catalog.views import _get_catalog_staff_context
    context = _get_catalog_staff_context(request, active_tab='reviews')
    context.update({
        'page_obj': page_obj,
        'reviews': page_obj.object_list,
        'total_count': paginator.count,
        'total_reviews': total_reviews,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'q': q,
        'status_filter': status_filter,
        'rating_filter': rating_filter,
        'verified_only': verified_only,
    })
    return render(request, 'reviews/manage_all_reviews.html', context)


# ==============================================================================
# 3. CUSTOMER ACCOUNT - MY REVIEWS
# ==============================================================================

@login_required(login_url='/accounts/login/')
def my_reviews_view(request):
    """
    Requirement 23: Customer Account My Reviews view.
    Displays all reviews authored by the logged-in user.
    """
    user_reviews = Review.objects.filter(
        user=request.user
    ).select_related('product', 'variant').prefetch_related('replies__user', 'media').order_by('-created_at')

    paginator = Paginator(user_reviews, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'reviews': page_obj.object_list,
        'total_reviews': paginator.count,
    }
    return render(request, 'reviews/my_reviews.html', context)
