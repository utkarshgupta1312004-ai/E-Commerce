import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class PaymentTransaction(models.Model):
    """
    Immutable ledger of payment transactions and gateway verification events.
    Records Razorpay order creation, payment ID, signature verification, and lifecycle states.
    """
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending Verification'),
        ('SUCCESS', 'Payment Successful'),
        ('FAILED', 'Payment Failed'),
        ('CANCELLED', 'Payment Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    GATEWAY_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('COD', 'Cash on Delivery'),
    ]

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique internal payment tracking identifier (e.g. TXN-YYYYMMDD-XXXXX)"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    order = models.ForeignKey(
        'orders.Order',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payment_transactions',
        help_text="Associated order once confirmed"
    )
    cart = models.ForeignKey(
        'cart.Cart',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payment_transactions',
        help_text="Cart snapshot at initiation"
    )
    shipping_address = models.ForeignKey(
        'accounts.Address',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='payment_transactions',
        help_text="Designated shipping address for order creation"
    )
    customer_notes = models.TextField(
        blank=True,
        default='',
        help_text="Customer delivery instructions"
    )

    # Gateway Details
    gateway = models.CharField(
        max_length=30,
        choices=GATEWAY_CHOICES,
        default='RAZORPAY',
        db_index=True
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total transaction amount in currency unit (e.g. INR)"
    )
    currency = models.CharField(
        max_length=10,
        default='INR'
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='INITIATED',
        db_index=True
    )

    # Razorpay Specific Identifiers
    razorpay_order_id = models.CharField(
        max_length=100,
        db_index=True,
        blank=True,
        default='',
        help_text="Razorpay Order ID (order_...)"
    )
    razorpay_payment_id = models.CharField(
        max_length=100,
        db_index=True,
        blank=True,
        default='',
        help_text="Razorpay Payment ID (pay_...)"
    )
    razorpay_signature = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="HMAC SHA256 Signature verified from Razorpay Checkout"
    )

    # Instrument Breakdown Details
    method = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Payment instrument (upi, card, netbanking, wallet)"
    )
    bank = models.CharField(max_length=100, blank=True, default='')
    wallet = models.CharField(max_length=100, blank=True, default='')
    vpa = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="UPI Virtual Payment Address if method is UPI"
    )

    # Diagnostic & Error Tracking
    error_code = models.CharField(max_length=100, blank=True, default='')
    error_description = models.TextField(blank=True, default='')
    error_source = models.CharField(max_length=100, blank=True, default='')
    error_step = models.CharField(max_length=100, blank=True, default='')
    error_reason = models.CharField(max_length=100, blank=True, default='')

    # Raw Payload Snapshot for Compliance & Auditing
    raw_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Complete JSON response payload from Razorpay"
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} ({self.gateway}) - ₹{self.amount} [{self.status}]"

    @classmethod
    def generate_transaction_id(cls) -> str:
        """Generates unique internal transaction identifier: TXN-YYYYMMDD-XXXXX"""
        date_str = timezone.now().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        candidate = f"TXN-{date_str}-{suffix}"
        while cls.objects.filter(transaction_id=candidate).exists():
            suffix = uuid.uuid4().hex[:6].upper()
            candidate = f"TXN-{date_str}-{suffix}"
        return candidate

    @property
    def is_successful(self) -> bool:
        return self.status == 'SUCCESS'
