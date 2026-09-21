from decimal import Decimal
from typing import Optional
from django.conf import settings
from django.db import models


class Wishlist(models.Model):
    """
    Wishlist container for authenticated customers.
    Stores products/variants saved for future purchase without altering inventory or cart state.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlists',
        help_text="Customer who owns this wishlist"
    )
    name = models.CharField(
        max_length=100,
        default='My Wishlist',
        help_text="Name of the wishlist (supports multiple wishlists in future)"
    )
    is_default = models.BooleanField(
        default=True,
        help_text="Primary wishlist for customer"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username}'s Wishlist ({self.items.count()} items)"

    @classmethod
    def get_default_for_user(cls, user):
        """Retrieves or creates the primary default wishlist for an authenticated user."""
        if not user or not user.is_authenticated:
            return None
        wishlist, _ = cls.objects.get_or_create(
            user=user,
            is_default=True,
            defaults={'name': 'My Wishlist'}
        )
        return wishlist

    @property
    def total_items(self) -> int:
        """Returns the total number of unique saved items in this wishlist."""
        return self.items.count()

    @property
    def in_stock_items_count(self) -> int:
        """Counts how many saved items are currently in stock and purchasable."""
        return sum(1 for item in self.items.select_related('product', 'variant') if item.is_in_stock)


class WishlistItem(models.Model):
    """
    Individual product or product variant entry inside a customer's Wishlist.
    Catalog remains the authoritative source of truth for pricing, stock, images, and metadata.
    """
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        help_text="Underlying Catalog Product"
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        help_text="Optional specific variant combination"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
        unique_together = ('wishlist', 'product', 'variant')
        ordering = ['-created_at']

    def __str__(self):
        v = f" ({self.variant.name})" if self.variant else ""
        return f"{self.wishlist.user.username} - {self.product.title}{v}"

    # -------------------------------------------------------------------------
    # Dynamic Catalog Attributes (Source of Truth Delegation)
    # -------------------------------------------------------------------------

    @property
    def title(self) -> str:
        if self.variant and self.variant.name:
            return f"{self.product.title} - {self.variant.name}"
        return self.product.title

    @property
    def effective_price(self) -> Decimal:
        """Always reads current dynamic Catalog price; never stores stale price."""
        if self.variant:
            return self.variant.effective_price
        return self.product.effective_price

    @property
    def compare_at_price(self) -> Optional[Decimal]:
        """Original / list price for discount badge rendering."""
        if self.variant and self.variant.compare_at_price:
            return self.variant.compare_at_price
        return self.product.compare_at_price

    @property
    def discount_percentage(self) -> int:
        if self.variant:
            return self.variant.discount_percentage
        return self.product.discount_percentage

    @property
    def primary_image_url(self) -> str:
        """Retrieves primary image from product or catalog."""
        return self.product.primary_image_url

    @property
    def available_stock(self) -> int:
        """Current real-time stock units available from inventory."""
        if self.variant:
            return self.variant.available_stock
        return self.product.total_available_stock

    @property
    def is_in_stock(self) -> bool:
        """True if the product/variant is currently active, public, and has available inventory."""
        if not (self.product.status == 'ACTIVE' and self.product.visibility == 'PUBLIC' and self.product.is_active):
            return False
        if self.variant:
            return self.variant.is_active and self.variant.is_in_stock
        return self.product.is_in_stock

    @property
    def stock_status_label(self) -> str:
        """Customer-friendly stock status message."""
        if not (self.product.status == 'ACTIVE' and self.product.visibility == 'PUBLIC' and self.product.is_active):
            return "Unavailable"
        if self.variant and not self.variant.is_active:
            return "Unavailable"
        avail = self.available_stock
        if avail <= 0:
            return "Out of Stock"
        elif avail <= 10:
            return f"Low Stock ({avail} left)"
        return "In Stock"

    @property
    def is_low_stock(self) -> bool:
        avail = self.available_stock
        return 0 < avail <= 10
