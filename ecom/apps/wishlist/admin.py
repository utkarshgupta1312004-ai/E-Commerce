from django.contrib import admin
from .models import Wishlist, WishlistItem


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    raw_id_fields = ('product', 'variant')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('product', 'variant', 'created_at', 'updated_at')


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'is_default', 'total_items_count', 'created_at', 'updated_at')
    list_filter = ('is_default', 'created_at')
    search_fields = ('user__username', 'user__email', 'name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WishlistItemInline]

    @admin.display(description='Total Items')
    def total_items_count(self, obj):
        return obj.items.count()


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'wishlist_owner', 'product', 'variant', 'effective_price_display', 'is_in_stock_display', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('wishlist__user__username', 'wishlist__user__email', 'product__title', 'variant__name')
    raw_id_fields = ('wishlist', 'product', 'variant')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Customer')
    def wishlist_owner(self, obj):
        return obj.wishlist.user.username

    @admin.display(description='Price')
    def effective_price_display(self, obj):
        return f"₹{obj.effective_price}"

    @admin.display(description='In Stock', boolean=True)
    def is_in_stock_display(self, obj):
        return obj.is_in_stock
