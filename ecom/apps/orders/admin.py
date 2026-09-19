from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        'product',
        'variant',
        'sku',
        'product_title',
        'variant_name',
        'unit_price',
        'quantity',
        'subtotal',
        'created_at',
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'user',
        'status',
        'payment_method',
        'payment_status',
        'total_amount',
        'created_at',
    )
    list_filter = (
        'status',
        'payment_method',
        'payment_status',
        'created_at',
    )
    search_fields = (
        'order_number',
        'user__username',
        'user__email',
        'shipping_name',
        'shipping_phone',
        'shipping_city',
    )
    readonly_fields = (
        'order_number',
        'user',
        'cart',
        'subtotal',
        'shipping_amount',
        'discount_amount',
        'tax_amount',
        'total_amount',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'cart', 'status', 'created_at', 'updated_at')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('Financial Ledger', {
            'fields': ('subtotal', 'shipping_amount', 'discount_amount', 'tax_amount', 'total_amount')
        }),
        ('Delivery Address Snapshot', {
            'fields': (
                'shipping_name',
                'shipping_phone',
                'shipping_street_address',
                'shipping_apartment',
                'shipping_city',
                'shipping_state',
                'shipping_postal_code',
                'shipping_country',
            )
        }),
        ('Notes', {
            'fields': ('customer_notes',)
        }),
    )
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_title', 'sku', 'unit_price', 'quantity', 'subtotal', 'created_at')
    search_fields = ('order__order_number', 'sku', 'product_title')
    list_filter = ('created_at',)
    readonly_fields = (
        'order',
        'product',
        'variant',
        'sku',
        'product_title',
        'variant_name',
        'unit_price',
        'quantity',
        'subtotal',
        'created_at',
    )
