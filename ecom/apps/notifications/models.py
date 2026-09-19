from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Customer notification entity.
    Strictly scoped to a specific customer user (Requirement 58 & 59).
    """
    EVENT_CHOICES = [
        ('ORDER_CONFIRMED', 'Order Confirmed'),
        ('ORDER_PACKED', 'Order Packed'),
        ('ORDER_SHIPPED', 'Order Shipped'),
        ('OUT_FOR_DELIVERY', 'Out for Delivery'),
        ('ORDER_DELIVERED', 'Order Delivered'),
        ('COD_PAYMENT_RECEIVED', 'COD Payment Received'),
        ('ORDER_COMPLETED', 'Order Completed'),
        ('DELIVERY_FAILED', 'Delivery Failed'),
        ('ORDER_RETURNED', 'Order Returned'),
        ('ORDER_CANCELLED', 'Order Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        db_index=True
    )
    order = models.ForeignKey(
        'orders.Order',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    event_type = models.CharField(
        max_length=50,
        choices=EVENT_CHOICES,
        db_index=True
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.event_type}] {self.user.username}: {self.title}"
