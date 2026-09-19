from django.conf import settings
from django.db import models
from django.db.models import F, Q, CheckConstraint, UniqueConstraint
from django.utils import timezone


class Warehouse(models.Model):
    """
    Physical distribution center or fulfillment warehouse storing Cartivo stock.
    Supports multiple warehouses with primary destination tracking.
    """
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Under Maintenance'),
    ]

    name = models.CharField(max_length=150, help_text="e.g. 'Central Distribution Hub'")
    code = models.CharField(max_length=50, unique=True, db_index=True, help_text="Unique code e.g. 'WH-CENTRAL-01'")
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, default='United States')
    contact_name = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_warehouses',
        help_text="Assigned warehouse supervisor or staff member"
    )
    is_primary = models.BooleanField(default=False, help_text="Default warehouse for automated fulfillment routing")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Warehouse'
        verbose_name_plural = 'Warehouses'
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        if self.is_primary:
            # Enforce single primary warehouse
            Warehouse.objects.filter(is_primary=True).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)

    @property
    def total_products_count(self):
        return self.stock_records.values('product').distinct().count()

    @property
    def total_units_on_hand(self):
        return self.stock_records.aggregate(total=models.Sum('on_hand_quantity'))['total'] or 0

    @property
    def total_units_available(self):
        records = self.stock_records.all()
        return sum(s.available_quantity for s in records)

    @property
    def total_units_reserved(self):
        return self.stock_records.aggregate(total=models.Sum('reserved_quantity'))['total'] or 0

    @property
    def low_stock_count(self):
        return self.stock_records.filter(status='LOW_STOCK').count()

    @property
    def out_of_stock_count(self):
        return self.stock_records.filter(status='OUT_OF_STOCK').count()

    @property
    def total_inventory_value(self):
        """Calculates total cost valuation using Product/Variant cost_price or base_price."""
        val = 0
        for stock in self.stock_records.select_related('product', 'variant'):
            unit_cost = stock.effective_cost_price
            val += unit_cost * stock.on_hand_quantity
        return val


class Location(models.Model):
    """
    Specific physical bin, rack, shelf, or staging zone within a Warehouse.
    e.g. 'A-01', 'B-04', 'DAMAGED-BAY', 'RECEIVING-01'.
    """
    LOCATION_TYPE_CHOICES = [
        ('STORAGE', 'Storage Bin / Shelf'),
        ('RECEIVING', 'Receiving Dock'),
        ('PICKING', 'Fast-Pick Area'),
        ('DISPATCH', 'Outbound Dispatch'),
        ('DAMAGED', 'Damaged / Hold Bay'),
        ('DEFAULT', 'General Warehouse Area'),
    ]

    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='locations')
    code = models.CharField(max_length=50, help_text="e.g. 'A-01', 'RACK-3B', 'DAMAGED'")
    name = models.CharField(max_length=100, blank=True, help_text="Optional human-readable label")
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES, default='STORAGE')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'
        ordering = ['warehouse', 'code']
        constraints = [
            UniqueConstraint(fields=['warehouse', 'code'], name='unique_warehouse_location_code')
        ]

    def __str__(self):
        return f"{self.warehouse.code} &bull; {self.code}"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        if not self.name:
            self.name = f"Zone {self.code}"
        super().save(*args, **kwargs)


class Stock(models.Model):
    """
    Represents actual inventory quantity of a Product or ProductVariant at a specific Warehouse & Location.
    Mathematical relationship:
        available_quantity = max(0, on_hand_quantity - reserved_quantity)
    """
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock'),
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('OVERSTOCK', 'Overstock'),
    ]

    product = models.ForeignKey(
        'catalog.Product',
        on_delete=models.CASCADE,
        related_name='stock_records',
        help_text="Underlying Catalog Product"
    )
    variant = models.ForeignKey(
        'catalog.ProductVariant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_records',
        help_text="Optional specific variant combination"
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='stock_records'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_records'
    )
    on_hand_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Physical count currently stored in warehouse"
    )
    reserved_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Units promised to pending orders or checkout holds"
    )
    incoming_quantity = models.PositiveIntegerField(
        default=0,
        help_text="Units in transit from suppliers or transfer orders"
    )
    reorder_point = models.PositiveIntegerField(
        default=10,
        help_text="Threshold quantity to trigger LOW_STOCK status and replenishment alerts"
    )
    safety_stock = models.PositiveIntegerField(
        default=5,
        help_text="Buffer stock to prevent stockouts from demand spikes"
    )
    maximum_stock = models.PositiveIntegerField(
        default=1000,
        help_text="Maximum capacity threshold before flagging OVERSTOCK"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='OUT_OF_STOCK',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock Item'
        verbose_name_plural = 'Stock Records'
        ordering = ['warehouse', 'product', 'variant']
        constraints = [
            CheckConstraint(condition=Q(on_hand_quantity__gte=0), name='stock_on_hand_gte_0'),
            CheckConstraint(condition=Q(reserved_quantity__gte=0), name='stock_reserved_gte_0'),
            CheckConstraint(condition=Q(incoming_quantity__gte=0), name='stock_incoming_gte_0'),
            UniqueConstraint(fields=['product', 'variant', 'warehouse', 'location'], name='unique_stock_product_variant_location')
        ]

    def __str__(self):
        sku_label = self.variant.sku if self.variant else (self.product.sku or self.product.title)
        return f"{sku_label} @ {self.warehouse.code}: {self.available_quantity} Avail (On Hand: {self.on_hand_quantity})"

    @property
    def available_quantity(self) -> int:
        """Units actually available for immediate purchase."""
        return max(0, self.on_hand_quantity - self.reserved_quantity)

    @property
    def is_in_stock(self) -> bool:
        return self.available_quantity > 0

    @property
    def sku(self) -> str:
        if self.variant:
            return self.variant.sku
        return self.product.sku or '—'

    @property
    def item_title(self) -> str:
        if self.variant:
            return f"{self.product.title} ({self.variant.name or self.variant.sku})"
        return self.product.title

    @property
    def effective_cost_price(self):
        if self.variant and self.variant.cost_price:
            return self.variant.cost_price
        if self.product.cost_price:
            return self.product.cost_price
        return self.product.base_price

    def recalculate_status(self):
        """Calculates and updates status based on current available_quantity."""
        avail = self.available_quantity
        if avail <= 0:
            new_status = 'OUT_OF_STOCK'
        elif avail <= self.reorder_point:
            new_status = 'LOW_STOCK'
        elif avail >= self.maximum_stock:
            new_status = 'OVERSTOCK'
        else:
            new_status = 'IN_STOCK'
        self.status = new_status
        return new_status

    def save(self, *args, **kwargs):
        self.recalculate_status()
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    """
    Append-only inventory ledger. Every change to physical or reserved stock
    creates an immutable record tracking Before -> Change -> After.
    """
    MOVEMENT_TYPE_CHOICES = [
        ('PURCHASE_RECEIPT', 'Purchase Receipt (Inbound)'),
        ('SALE', 'Sale Deduction (Outbound)'),
        ('RETURN', 'Customer Return (Inbound)'),
        ('TRANSFER_IN', 'Warehouse Transfer In'),
        ('TRANSFER_OUT', 'Warehouse Transfer Out'),
        ('ADJUSTMENT_IN', 'Adjustment (Count Increase)'),
        ('ADJUSTMENT_OUT', 'Adjustment (Count Decrease)'),
        ('DAMAGE', 'Damaged Stock (Written Off)'),
        ('LOSS', 'Shrinkage / Lost'),
        ('RESERVATION', 'Stock Reserved for Order'),
        ('RESERVATION_RELEASE', 'Reservation Released'),
        ('CANCELLATION', 'Order Cancellation Restock'),
    ]
    MOVEMENT_TYPES = MOVEMENT_TYPE_CHOICES

    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='movements')
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.CASCADE, null=True, blank=True, related_name='movements')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='movements')
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='movements')
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPE_CHOICES, db_index=True)
    quantity = models.IntegerField(help_text="Signed quantity change (+10, -2)")
    before_quantity = models.IntegerField(help_text="Physical on-hand quantity before movement")
    after_quantity = models.IntegerField(help_text="Physical on-hand quantity after movement")
    before_reserved = models.IntegerField(default=0, help_text="Reserved quantity before movement")
    after_reserved = models.IntegerField(default=0, help_text="Reserved quantity after movement")
    reference_type = models.CharField(max_length=50, blank=True, db_index=True, help_text="e.g. 'ORDER', 'ADJUSTMENT', 'TRANSFER'")
    reference_id = models.CharField(max_length=100, blank=True, db_index=True, help_text="e.g. Order ID, Invoice #, Transfer #")
    reason = models.TextField(blank=True, help_text="Operational notes or justification")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'
        ordering = ['-created_at']

    def __str__(self):
        sku = self.variant.sku if self.variant else (self.product.sku or self.product.title)
        sign = "+" if self.quantity > 0 else ""
        return f"{self.movement_type}: {sku} {sign}{self.quantity} ({self.before_quantity} &rarr; {self.after_quantity})"


class StockReservation(models.Model):
    """
    Tracks inventory holds reserved during order checkout prior to fulfillment.
    Prevents overselling between checkout initiation and payment capture.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending (Active Hold)'),
        ('FULFILLED', 'Fulfilled (Converted to Sale)'),
        ('RELEASED', 'Released (Cancelled Hold)'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='reservations')
    quantity = models.PositiveIntegerField(help_text="Number of units held")
    reference_type = models.CharField(max_length=50, default='ORDER', db_index=True)
    reference_id = models.CharField(max_length=100, db_index=True, help_text="Order number or Cart session ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_reservations'
    )
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional reservation expiration time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Stock Reservation'
        verbose_name_plural = 'Stock Reservations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reservation #{self.id}: {self.quantity} units for {self.reference_type} #{self.reference_id} [{self.status}]"


class StockAdjustment(models.Model):
    """
    Controlled manual stock correction with mandatory audit trail.
    Directs to `StockMovement` as its ledger partner.
    """
    REASON_CHOICES = [
        ('DAMAGED', 'Damaged Goods'),
        ('LOST', 'Lost / Shrinkage'),
        ('FOUND', 'Found / Extra Discovered'),
        ('COUNTING_ERROR', 'Physical Counting Discrepancy'),
        ('OPENING_STOCK', 'Initial Opening Stock'),
        ('MANUAL_CORRECTION', 'Managerial Correction'),
        ('OTHER', 'Other / Custom Justification'),
    ]

    ADJUSTMENT_TYPE_CHOICES = [
        ('INCREASE', 'Increase On-Hand (+Qty)'),
        ('DECREASE', 'Decrease On-Hand (-Qty)'),
        ('SET', 'Set Absolute Count (=Qty)'),
    ]

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='adjustments')
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Quantity delta or absolute target count")
    previous_on_hand = models.IntegerField()
    new_on_hand = models.IntegerField()
    reason = models.CharField(max_length=40, choices=REASON_CHOICES)
    notes = models.TextField(blank=True, help_text="Audit explanation for this adjustment")
    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_adjustments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Stock Adjustment'
        verbose_name_plural = 'Stock Adjustments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Adjustment #{self.id} on {self.stock}: {self.previous_on_hand} &rarr; {self.new_on_hand} ({self.reason})"

    @property
    def after_quantity(self) -> int:
        return self.new_on_hand

    @property
    def before_quantity(self) -> int:
        return self.previous_on_hand
