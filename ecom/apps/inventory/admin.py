from django.contrib import admin
from .models import (
    Warehouse,
    Location,
    Stock,
    StockMovement,
    StockReservation,
    StockAdjustment,
)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_primary', 'status', 'manager', 'created_at']
    list_filter = ['status', 'is_primary']
    search_fields = ['code', 'name', 'address']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['code', 'warehouse', 'name', 'location_type', 'is_active']
    list_filter = ['warehouse', 'location_type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = [
        'product',
        'variant',
        'warehouse',
        'on_hand_quantity',
        'reserved_quantity',
        'available_quantity',
        'reorder_point',
        'status',
        'updated_at',
    ]
    list_filter = ['warehouse', 'status']
    search_fields = ['product__title', 'product__sku', 'variant__sku']
    readonly_fields = ['status', 'created_at', 'updated_at']


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'movement_type',
        'product',
        'warehouse',
        'quantity',
        'before_quantity',
        'after_quantity',
        'reference_type',
        'reference_id',
        'performed_by',
    ]
    list_filter = ['movement_type', 'warehouse', 'reference_type']
    search_fields = ['product__title', 'reference_id', 'reason']
    readonly_fields = [
        'product', 'variant', 'warehouse', 'location',
        'movement_type', 'quantity', 'before_quantity', 'after_quantity',
        'before_reserved', 'after_reserved', 'reference_type', 'reference_id',
        'reason', 'performed_by', 'created_at',
    ]

    def has_add_permission(self, request):
        # Movements are append-only generated via InventoryService
        return False

    def has_delete_permission(self, request, obj=None):
        # Immutable ledger
        return False


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ['id', 'stock', 'quantity', 'status', 'reference_type', 'reference_id', 'created_at']
    list_filter = ['status', 'reference_type']
    search_fields = ['stock__product__title', 'reference_id']


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = [
        'created_at',
        'stock',
        'adjustment_type',
        'reason',
        'previous_on_hand',
        'new_on_hand',
        'adjusted_by',
    ]
    list_filter = ['adjustment_type', 'reason']
    search_fields = ['stock__product__title', 'notes']
