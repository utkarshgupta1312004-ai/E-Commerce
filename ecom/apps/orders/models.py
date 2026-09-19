import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Order(models.Model):
    """
    Permanent, immutable record of a completed customer purchase.
    Cart is temporary; Order is permanent.
    """
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('PROCESSING', 'Processing & Packed'),
        ('SHIPPED', 'Dispatched / In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('COD', 'Cash on Delivery'),
        # Future placeholders:
        # ('UPI', 'Unified Payments Interface (UPI)'),
        # ('CARD', 'Credit / Debit Card'),
        # ('NET_BANKING', 'Net Banking'),
        # ('WALLET', 'Digital Wallet'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]

    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Human-readable unique order identifier (e.g. ORD-20260918-00001)"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    cart = models.ForeignKey(
        'cart.Cart',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders',
        help_text="Source shopping cart converted into this order"
    )
    shipping_address = models.ForeignKey(
        'accounts.Address',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='orders_shipped'
    )

    # Immutable Delivery Address Snapshot
    shipping_name = models.CharField(max_length=150)
    shipping_phone = models.CharField(max_length=30, blank=True, default='')
    shipping_street_address = models.CharField(max_length=255)
    shipping_apartment = models.CharField(max_length=100, blank=True, default='')
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default='United States')

    # Lifecycle & Payment
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='CONFIRMED',
        db_index=True
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        default='COD',
        db_index=True
    )
    payment_status = models.CharField(
        max_length=30,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )

    # Delivery Tracking & Location Details
    delivery_partner = models.CharField(
        max_length=120,
        blank=True,
        default='Cartivo Express Delivery',
        help_text="Designated logistics carrier"
    )
    tracking_number = models.CharField(
        max_length=80,
        blank=True,
        default='',
        help_text="Courier parcel tracking number"
    )
    current_location = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Current physical checkpoint location of the shipment"
    )
    estimated_delivery_date = models.CharField(
        max_length=80,
        blank=True,
        default='',
        help_text="Target delivery window / SLA"
    )

    # Financial Ledger Breakdown
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    customer_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.order_number} - {self.user.username} (₹{self.total_amount})"

    @classmethod
    def generate_order_number(cls) -> str:
        """
        Generates a unique human-readable order number: ORD-YYYYMMDD-XXXXX
        """
        date_str = timezone.now().strftime('%Y%m%d')
        # Use random hex string to guarantee uniqueness under concurrency
        suffix = uuid.uuid4().hex[:5].upper()
        candidate = f"ORD-{date_str}-{suffix}"
        while cls.objects.filter(order_number=candidate).exists():
            suffix = uuid.uuid4().hex[:5].upper()
            candidate = f"ORD-{date_str}-{suffix}"
        return candidate

    @property
    def formatted_shipping_address(self) -> str:
        parts = [self.shipping_street_address]
        if self.shipping_apartment:
            parts.append(self.shipping_apartment)
        parts.append(f"{self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}")
        parts.append(self.shipping_country)
        return ", ".join(filter(None, parts))

    @property
    def total_items_count(self) -> int:
        return sum(item.quantity for item in self.items.all())

    @property
    def tracking_code(self) -> str:
        """Returns carrier tracking number or default formatted tracking identifier."""
        if self.tracking_number:
            return self.tracking_number
        clean_num = self.order_number.replace('ORD-', '')
        return f"CRTV-TRK-{clean_num}"

    @property
    def delivery_step_index(self) -> int:
        """Numeric index (1-5) representing milestone progression along the delivery journey."""
        mapping = {
            'CONFIRMED': 1,
            'PROCESSING': 2,
            'SHIPPED': 3,
            'OUT_FOR_DELIVERY': 4,
            'DELIVERED': 5,
            'CANCELLED': 0,
        }
        return mapping.get(self.status, 1)

    @property
    def delivery_progress_percent(self) -> int:
        """Progress bar percentage for delivery visualization."""
        mapping = {
            'CONFIRMED': 20,
            'PROCESSING': 40,
            'SHIPPED': 65,
            'OUT_FOR_DELIVERY': 85,
            'DELIVERED': 100,
            'CANCELLED': 0,
        }
        return mapping.get(self.status, 20)

    @property
    def active_location_display(self) -> str:
        """Returns physical checkpoint location or contextual default based on delivery state."""
        if self.current_location:
            return self.current_location
        defaults = {
            'CONFIRMED': 'Cartivo Central Fulfillment Center - Sorting & Packaging',
            'PROCESSING': 'Warehouse Dispatch Bay - Quality Inspection & Package Seal',
            'SHIPPED': 'In Transit - Regional Distribution Hub',
            'OUT_FOR_DELIVERY': 'Local Distribution Station - Out for Delivery by Courier Agent',
            'DELIVERED': f"Delivered to {self.shipping_city} destination address",
            'CANCELLED': 'Order Cancelled - Shipment Voided',
        }
        return defaults.get(self.status, 'Cartivo Central Fulfillment Center')


class OrderItem(models.Model):
    """
    Immutable line item snapshot of an order.
    Preserves product title, SKU, variant configuration, and unit price permanently,
    even if the product is later modified or deleted.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'catalog.Product',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='order_items'
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='order_items'
    )

    # Immutable historical snapshots
    sku = models.CharField(max_length=100, db_index=True)
    product_title = models.CharField(max_length=255)
    variant_name = models.CharField(max_length=200, blank=True, default='')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        ordering = ['created_at']

    def __str__(self):
        v = f" ({self.variant_name})" if self.variant_name else ""
        return f"{self.order.order_number} - {self.product_title}{v} x {self.quantity}"


class DeliveryCheckpoint(models.Model):
    """
    Historical log of physical shipment checkpoints and carrier transit events.
    Enables rich chronological order journey tracking for both customers and dispatch staff.
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='checkpoints')
    status = models.CharField(max_length=30, choices=Order.STATUS_CHOICES, default='CONFIRMED')
    location = models.CharField(max_length=200, help_text="Physical facility, hub, or city of checkpoint")
    notes = models.CharField(max_length=255, blank=True, default='', help_text="Event description or courier notes")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'Delivery Checkpoint'
        verbose_name_plural = 'Delivery Checkpoints'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.order.order_number} - {self.status} at {self.location}"
