from django.contrib import admin
from .models import Review, ReviewMedia, ReviewReply, ReviewVote


class ReviewReplyInline(admin.StackedInline):
    model = ReviewReply
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class ReviewMediaInline(admin.TabularInline):
    model = ReviewMedia
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'author_display_name',
        'rating',
        'status',
        'is_verified_purchase',
        'helpful_count',
        'created_at',
    )
    list_filter = ('status', 'rating', 'is_verified_purchase', 'created_at')
    search_fields = (
        'product__title',
        'product__sku',
        'user__username',
        'user__first_name',
        'user__email',
        'title',
        'comment',
    )
    list_editable = ('status',)
    raw_id_fields = ('product', 'variant', 'user', 'order_item')
    readonly_fields = ('created_at', 'updated_at', 'helpful_count')
    inlines = [ReviewReplyInline, ReviewMediaInline]
    actions = ['approve_reviews', 'reject_reviews']

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        from .services import ReviewService
        for review in queryset:
            review.status = Review.STATUS_APPROVED
            review.save(update_fields=['status', 'updated_at'])
            ReviewService.update_product_rating_cache(review.product)
        self.message_user(request, f"{queryset.count()} reviews successfully approved.")

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        from .services import ReviewService
        for review in queryset:
            review.status = Review.STATUS_REJECTED
            review.save(update_fields=['status', 'updated_at'])
            ReviewService.update_product_rating_cache(review.product)
        self.message_user(request, f"{queryset.count()} reviews rejected.")


@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'responder_name', 'created_at')
    search_fields = ('review__product__title', 'reply_text', 'user__username')
    raw_id_fields = ('review', 'user')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReviewVote)
class ReviewVoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'is_helpful', 'created_at')
    list_filter = ('is_helpful', 'created_at')
    raw_id_fields = ('review', 'user')
    readonly_fields = ('created_at',)
