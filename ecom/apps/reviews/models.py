from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Review(models.Model):
    """
    Customer review and rating entity connected to catalog.Product.
    Manages review content, rating, verification status, and moderation.
    Product data is NOT duplicated here; Product remains the source of truth.
    """
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending Moderation'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    )

    RATING_CHOICES = (
        (1, '1 Star - Poor'),
        (2, '2 Stars - Fair'),
        (3, '3 Stars - Good'),
        (4, '4 Stars - Very Good'),
        (5, '5 Stars - Excellent'),
    )

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="Product being reviewed"
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        help_text="Optional specific variant purchased by customer"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="Customer who authored the review"
    )
    order_item = models.ForeignKey(
        'orders.OrderItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        help_text="Delivered order line item for verified purchase linkage"
    )

    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Customer rating score from 1 to 5 stars"
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Short headline summary of the review"
    )
    comment = models.TextField(
        help_text="Detailed customer review commentary"
    )

    is_verified_purchase = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Validated server-side against actual delivered customer orders"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_APPROVED,
        db_index=True,
        help_text="Publication moderation state"
    )
    helpful_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of helpful community upvotes"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Review'
        verbose_name_plural = 'Customer Reviews'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_product_review'
            )
        ]
        indexes = [
            models.Index(fields=['product', 'status', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.rating}★ Review by {self.author_display_name} for {self.product.title}"

    @property
    def author_display_name(self) -> str:
        """
        Safe customer display name protecting customer privacy.
        Never reveals email, phone, or internal IDs publicly.
        """
        full_name = self.user.get_full_name()
        if full_name and full_name.strip():
            names = full_name.strip().split()
            if len(names) > 1:
                return f"{names[0]} {names[-1][0]}."
            return names[0]
        if self.user.username:
            u = self.user.username
            if '@' in u:
                u = u.split('@')[0]
            if len(u) > 4:
                return f"{u[:2]}***{u[-2:]}"
            return u
        return "Customer"

    @property
    def official_reply(self):
        """Returns the latest official management/seller reply if available."""
        return self.replies.order_by('-created_at').first()

    def get_rating_stars(self):
        """Returns list of 5 booleans indicating filled state for stars."""
        return [i <= self.rating for i in range(1, 6)]


class ReviewMedia(models.Model):
    """
    Optional photo/media evidence uploaded by customer with their review.
    Enforces file size and format validation.
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='media'
    )
    image = models.ImageField(
        upload_to='reviews/%Y/%m/',
        blank=True,
        null=True,
        help_text="Customer review photo"
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text="Direct URL fallback or CDN image"
    )
    caption = models.CharField(
        max_length=200,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Review Media'
        verbose_name_plural = 'Review Media'
        ordering = ['created_at']

    @property
    def effective_image_url(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url or ''

    def __str__(self):
        return f"Media for Review #{self.review_id}"


class ReviewReply(models.Model):
    """
    Official seller or staff response to a customer review.
    Visible publicly directly beneath the customer's review on Product Detail.
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_review_replies'
    )
    reply_text = models.TextField(
        help_text="Official response from seller or store support"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Review Reply'
        verbose_name_plural = 'Review Replies'
        ordering = ['created_at']

    @property
    def responder_name(self) -> str:
        if self.user and self.user.is_superuser:
            return "Cartivo Official Team"
        if self.user and (self.user.first_name or self.user.last_name):
            return f"Seller ({self.user.first_name or 'Staff'})"
        return "Seller Response"

    def __str__(self):
        return f"Reply to Review #{self.review_id} by {self.responder_name}"


class ReviewVote(models.Model):
    """
    Helpful vote cast by authenticated customer for a review.
    Enforces 1 vote per customer per review to prevent vote manipulation.
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_votes'
    )
    is_helpful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Review Vote'
        verbose_name_plural = 'Review Votes'
        constraints = [
            models.UniqueConstraint(
                fields=['review', 'user'],
                name='unique_review_user_vote'
            )
        ]

    def __str__(self):
        return f"User #{self.user_id} voted helpful={self.is_helpful} on Review #{self.review_id}"
