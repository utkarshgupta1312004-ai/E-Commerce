from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id',
        'user',
        'order_link',
        'amount_display',
        'gateway',
        'method',
        'status_badge',
        'razorpay_payment_id',
        'created_at',
    )
    list_filter = ('status', 'gateway', 'method', 'created_at')
    search_fields = (
        'transaction_id',
        'user__username',
        'user__email',
        'order__order_number',
        'razorpay_order_id',
        'razorpay_payment_id',
        'vpa',
    )
    readonly_fields = (
        'transaction_id',
        'created_at',
        'updated_at',
        'raw_response',
    )
    date_hierarchy = 'created_at'

    def amount_display(self, obj):
        return f"₹{obj.amount} {obj.currency}"
    amount_display.short_description = 'Amount'

    def order_link(self, obj):
        if obj.order:
            return format_html(
                '<a href="/admin/orders/order/{}/change/">{}</a>',
                obj.order.id,
                obj.order.order_number
            )
        return "-"
    order_link.short_description = 'Order'

    def status_badge(self, obj):
        colors = {
            'SUCCESS': '#059669',
            'PENDING': '#d97706',
            'INITIATED': '#2563eb',
            'FAILED': '#dc2626',
            'CANCELLED': '#64748b',
            'REFUNDED': '#7c3aed',
        }
        bg = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px;">{}</span>',
            bg,
            obj.status
        )
    status_badge.short_description = 'Status'
