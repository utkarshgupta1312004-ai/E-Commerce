from decimal import Decimal
from django.conf import settings
from django.db import models


class Cart(models.Model):
    """
    Shopping Cart for customers (both guest session and authenticated users).
    Before order: temporary shopping state (ACTIVE).
    After order: converted to permanent Order and marked CONVERTED.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('CONVERTED', 'Converted'),
        ('ABANDONED', 'Abandoned'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='carts'
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'
        ordering = ['-updated_at']

    def __str__(self):
        owner = self.user.username if self.user else f"Guest ({self.session_key})"
        return f"Cart #{self.pk} - {owner} ({self.status})"

    @property
    def total_items(self) -> int:
        """Returns the total number of physical item units in the cart."""
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self) -> Decimal:
        """Calculates total price of all items in cart."""
        return sum((item.subtotal for item in self.items.all()), Decimal('0.00'))

    @property
    def is_empty(self) -> bool:
        return self.items.count() == 0


class CartItem(models.Model):
    """
    Line item inside a shopping cart representing a product or specific product variant.
    """
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='cart_items')
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'
        unique_together = ('cart', 'product', 'variant')
        ordering = ['created_at']

    def __str__(self):
        v_name = f" ({self.variant.name})" if self.variant else ""
        return f"{self.product.title}{v_name} x {self.quantity}"

    @property
    def unit_price(self) -> Decimal:
        if self.variant:
            return self.variant.effective_price
        return self.product.effective_price

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def sku(self) -> str:
        if self.variant and self.variant.sku:
            return self.variant.sku
        return self.product.sku or self.product.title

    @property
    def available_stock(self) -> int:
        if self.variant:
            return self.variant.available_stock
        return self.product.total_available_stock
