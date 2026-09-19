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
        ('READY_TO_PACK', 'Ready to Pack'),
        ('PACKED', 'Packed'),
        ('READY_TO_SHIP', 'Ready to Ship'),
        ('SHIPPED', 'Dispatched / In Transit'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Delivery Failed'),
        ('RETURNED', 'Returned'),
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
    tracking_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text="Public courier parcel tracking link"
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
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when order was delivered"
    )

    # Internal Operational Fields (Hidden from Customer)
    delivery_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of delivery attempts made"
    )
    delivery_failure_reason = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Internal failure reason if delivery fails"
    )
    cod_received_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Actual cash collected"
    )
    cod_collected_by = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text="Staff or courier agent who collected cash"
    )
    internal_notes = models.TextField(
        blank=True,
        default='',
        help_text="Internal operational notes not visible to customer"
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
    def address_snapshot_lines(self) -> list[str]:
        """Returns structured address lines strictly from this order's immutable snapshot."""
        lines = [self.shipping_name]
        street = self.shipping_street_address
        if self.shipping_apartment:
            street += f", {self.shipping_apartment}"
        lines.append(street)
        lines.append(f"{self.shipping_city}, {self.shipping_state} {self.shipping_postal_code}")
        lines.append(self.shipping_country)
        return lines

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
    def customer_friendly_status(self) -> str:
        """
        Requirement 52: Customer-friendly status sentences.
        Does not expose internal technical status names to customers.
        """
        friendly_map = {
            'READY_TO_PACK': "Your order is being prepared",
            'PACKED': "Your order has been packed",
            'READY_TO_SHIP': "Your order is ready for dispatch",
            'SHIPPED': "Your order has been shipped",
            'OUT_FOR_DELIVERY': "Your order is out for delivery",
            'DELIVERED': "Your order has been delivered",
            'FAILED': "Delivery attempt was unsuccessful",
            'RETURNED': "Your order has been returned",
            'CONFIRMED': "Your order has been confirmed",
            'PROCESSING': "Your order is being prepared",
            'CANCELLED': "Your order has been cancelled",
        }
        return friendly_map.get(self.status, "Your order is being processed")

    @property
    def customer_status_label(self) -> str:
        """Short customer-friendly status badge text."""
        label_map = {
            'READY_TO_PACK': "Preparing",
            'PACKED': "Packed",
            'READY_TO_SHIP': "Ready for Dispatch",
            'SHIPPED': "Shipped",
            'OUT_FOR_DELIVERY': "Out for Delivery",
            'DELIVERED': "Delivered",
            'FAILED': "Delivery Failed",
            'RETURNED': "Returned",
            'CONFIRMED': "Confirmed",
            'PROCESSING': "Preparing",
            'CANCELLED': "Cancelled",
        }
        return label_map.get(self.status, self.get_status_display())

    @property
    def customer_payment_display(self) -> str:
        """
        Requirement 53: Customer-friendly payment status label.
        Shows 'Payment Received' or 'Payment Pending' for COD.
        """
        if self.payment_method == 'COD':
            if self.payment_status == 'PAID':
                return "Payment Received"
            return "Payment Pending"
        if self.payment_status == 'PAID':
            return "Payment Completed"
        if self.payment_status == 'FAILED':
            return "Payment Failed"
        return "Payment Pending"

    @property
    def customer_payment_note(self) -> str:
        """
        Requirement 54: COD Customer Flow exact messaging.
        - Order placed: 'Cash on Delivery — Payment pending'
        - After delivery, cash pending: 'Order delivered. Payment confirmation pending.'
        - After cash confirmed: 'Payment received'
        """
        if self.payment_method == 'COD':
            if self.payment_status == 'PAID':
                return "Payment received"
            elif self.status == 'DELIVERED':
                return "Order delivered. Payment confirmation pending."
            return "Cash on Delivery — Payment pending"
        if self.payment_status == 'PAID':
            return "Payment received"
        return "Payment pending"

    @property
    def can_cancel(self) -> bool:
        """
        Requirement 61: Only allow cancellation according to valid order/shipping status.
        Allowed on CONFIRMED or PENDING.
        Restricted on PACKED, SHIPPED, OUT_FOR_DELIVERY, DELIVERED, etc.
        """
        return self.status in ('CONFIRMED', 'PENDING')

    @property
    def is_shipped_or_transit(self) -> bool:
        return self.status in ('SHIPPED', 'OUT_FOR_DELIVERY')

    @property
    def is_delivered(self) -> bool:
        return self.status == 'DELIVERED'

    @property
    def delivery_step_index(self) -> int:
        """Numeric index (1-5) representing milestone progression along the delivery journey."""
        mapping = {
            'CONFIRMED': 1,
            'PROCESSING': 2,
            'READY_TO_PACK': 2,
            'PACKED': 2,
            'READY_TO_SHIP': 2,
            'SHIPPED': 3,
            'OUT_FOR_DELIVERY': 4,
            'DELIVERED': 5,
            'CANCELLED': 0,
            'FAILED': 0,
            'RETURNED': 0,
        }
        return mapping.get(self.status, 1)

    @property
    def delivery_progress_percent(self) -> int:
        """Progress bar percentage for delivery visualization."""
        mapping = {
            'CONFIRMED': 20,
            'PROCESSING': 35,
            'READY_TO_PACK': 35,
            'PACKED': 50,
            'READY_TO_SHIP': 50,
            'SHIPPED': 70,
            'OUT_FOR_DELIVERY': 85,
            'DELIVERED': 100,
            'CANCELLED': 0,
            'FAILED': 0,
            'RETURNED': 0,
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
            'READY_TO_PACK': 'Fulfillment Center - Item Picking in Progress',
            'PACKED': 'Packing Station - Carton Sealed & Labelled',
            'READY_TO_SHIP': 'Outbound Dock - Awaiting Courier Dispatch',
            'SHIPPED': 'In Transit - Regional Distribution Hub',
            'OUT_FOR_DELIVERY': 'Local Distribution Station - Out for Delivery by Courier Agent',
            'DELIVERED': f"Delivered to {self.shipping_city} destination address",
            'FAILED': f"Delivery attempt in {self.shipping_city} could not be completed",
            'RETURNED': 'Returned to Central Fulfillment Center',
            'CANCELLED': 'Order Cancelled - Shipment Voided',
        }
        return defaults.get(self.status, 'Cartivo Central Fulfillment Center')

    @property
    def customer_timeline(self) -> list[dict]:
        """
        Requirement 51: Dynamic Customer Shipping Timeline.
        Generated dynamically from actual Shipment/Order checkpoints and history.
        Do NOT hardcode statuses.
        """
        cps = list(self.checkpoints.filter(is_customer_visible=True).order_by('timestamp'))

        # Map checkpoints to key milestone categories
        cp_by_step = {}
        for cp in cps:
            if cp.status in ('CONFIRMED',) and 'CONFIRMED' not in cp_by_step:
                cp_by_step['CONFIRMED'] = cp
            elif cp.status in ('READY_TO_PACK', 'PROCESSING', 'PACKED', 'READY_TO_SHIP') and 'PACKED' not in cp_by_step:
                cp_by_step['PACKED'] = cp
            elif cp.status in ('SHIPPED',) and 'SHIPPED' not in cp_by_step:
                cp_by_step['SHIPPED'] = cp
            elif cp.status in ('OUT_FOR_DELIVERY',) and 'OUT_FOR_DELIVERY' not in cp_by_step:
                cp_by_step['OUT_FOR_DELIVERY'] = cp
            elif cp.status in ('DELIVERED',) and 'DELIVERED' not in cp_by_step:
                cp_by_step['DELIVERED'] = cp

        curr_step = self.delivery_step_index

        milestones = [
            {
                'key': 'CONFIRMED',
                'title': 'Order Confirmed',
                'completed': self.status != 'CANCELLED',
                'timestamp': cp_by_step.get('CONFIRMED').timestamp if cp_by_step.get('CONFIRMED') else self.created_at,
            },
            {
                'key': 'PACKED',
                'title': 'Order Packed',
                'completed': curr_step >= 2 or 'PACKED' in cp_by_step,
                'timestamp': cp_by_step.get('PACKED').timestamp if cp_by_step.get('PACKED') else None,
            },
            {
                'key': 'SHIPPED',
                'title': 'Shipped',
                'completed': curr_step >= 3 or 'SHIPPED' in cp_by_step,
                'timestamp': cp_by_step.get('SHIPPED').timestamp if cp_by_step.get('SHIPPED') else None,
            },
            {
                'key': 'OUT_FOR_DELIVERY',
                'title': 'Out for Delivery',
                'completed': curr_step >= 4 or 'OUT_FOR_DELIVERY' in cp_by_step,
                'timestamp': cp_by_step.get('OUT_FOR_DELIVERY').timestamp if cp_by_step.get('OUT_FOR_DELIVERY') else None,
            },
            {
                'key': 'DELIVERED',
                'title': 'Delivered',
                'completed': curr_step >= 5 or self.status == 'DELIVERED',
                'timestamp': self.delivered_at or (cp_by_step.get('DELIVERED').timestamp if cp_by_step.get('DELIVERED') else None),
            },
        ]

        formatted_timeline = []
        for m in milestones:
            if m['completed']:
                ts = m['timestamp']
                if ts:
                    formatted_time = ts.strftime('%d %b, %I:%M %p')
                else:
                    formatted_time = "Completed"
                is_pending = False
            else:
                formatted_time = "Pending"
                is_pending = True

            formatted_timeline.append({
                'key': m['key'],
                'title': m['title'],
                'completed': m['completed'],
                'is_pending': is_pending,
                'display_time': formatted_time,
                'timestamp': m['timestamp'],
            })

        return formatted_timeline


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
    is_customer_visible = models.BooleanField(default=True, help_text="Whether this checkpoint is customer visible")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = 'Delivery Checkpoint'
        verbose_name_plural = 'Delivery Checkpoints'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.order.order_number} - {self.status} at {self.location}"
