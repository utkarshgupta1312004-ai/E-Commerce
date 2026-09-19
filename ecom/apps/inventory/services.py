"""
Inventory Service Layer for Cartivo E-Commerce.
Provides transactional, concurrency-safe inventory operations utilizing
database row-level locking (select_for_update) to prevent race conditions,
overselling, and negative stock.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import (
    Warehouse,
    Location,
    Stock,
    StockMovement,
    StockReservation,
    StockAdjustment,
)


class InventoryError(Exception):
    """Base exception for inventory operations."""
    pass


class InsufficientStockError(InventoryError):
    """Raised when available stock is lower than requested quantity."""
    pass


class StockValidationError(InventoryError):
    """Raised when invalid parameters or negative quantities are passed."""
    pass


class InvalidLocationError(InventoryError):
    """Raised when location does not belong to specified warehouse."""
    pass


class InventoryService:
    """
    Central service for all inventory operations.
    Guarantees that every physical or reserved change produces an immutable
    audit entry in StockMovement.
    """

    @classmethod
    def get_or_create_stock(
        cls,
        product,
        warehouse,
        variant=None,
        location=None,
        default_reorder_point=10,
        default_safety_stock=5
    ) -> Stock:
        """
        Retrieves or initializes a Stock record for a Product/Variant at a Warehouse.
        If location is specified, verifies it belongs to the warehouse.
        """
        if location and location.warehouse_id != warehouse.id:
            raise InvalidLocationError(f"Location {location.code} does not belong to Warehouse {warehouse.code}.")

        stock, created = Stock.objects.get_or_create(
            product=product,
            variant=variant,
            warehouse=warehouse,
            location=location,
            defaults={
                'on_hand_quantity': 0,
                'reserved_quantity': 0,
                'reorder_point': default_reorder_point,
                'safety_stock': default_safety_stock,
                'status': 'OUT_OF_STOCK',
            }
        )
        return stock

    @classmethod
    @transaction.atomic
    def increase_stock(
        cls,
        product,
        warehouse,
        quantity: int,
        variant=None,
        location=None,
        movement_type='PURCHASE_RECEIPT',
        reference_type='',
        reference_id='',
        reason='',
        performed_by=None
    ) -> Stock:
        """
        Increases on-hand physical stock atomically and writes to StockMovement ledger.
        """
        if quantity <= 0:
            raise StockValidationError(f"Increase quantity must be positive, got {quantity}.")

        stock = cls.get_or_create_stock(product, warehouse, variant=variant, location=location)

        # Acquire exclusive row lock
        stock = Stock.objects.select_for_update().get(pk=stock.pk)

        before_qty = stock.on_hand_quantity
        before_res = stock.reserved_quantity
        after_qty = before_qty + quantity

        stock.on_hand_quantity = after_qty
        stock.save()

        # Ledger transaction
        StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=warehouse,
            location=location,
            movement_type=movement_type,
            quantity=quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            before_reserved=before_res,
            after_reserved=before_res,
            reference_type=reference_type,
            reference_id=str(reference_id),
            reason=reason or f"Stock increased by {quantity} units",
            performed_by=performed_by
        )
        return stock

    @classmethod
    @transaction.atomic
    def decrease_stock(
        cls,
        product,
        warehouse,
        quantity: int,
        variant=None,
        location=None,
        movement_type='SALE',
        reference_type='ORDER',
        reference_id='',
        reason='',
        performed_by=None
    ) -> Stock:
        """
        Deducts physical stock directly (e.g. for direct counter sales or adjustments).
        Ensures stock cannot go below zero or below currently reserved quantity.
        """
        if quantity <= 0:
            raise StockValidationError(f"Decrease quantity must be positive, got {quantity}.")

        stock = cls.get_or_create_stock(product, warehouse, variant=variant, location=location)

        # Acquire exclusive row lock
        stock = Stock.objects.select_for_update().get(pk=stock.pk)

        if stock.available_quantity < quantity:
            sku = variant.sku if variant else (product.sku or product.title)
            raise InsufficientStockError(
                f"Insufficient stock for {sku} in {warehouse.name}. "
                f"Available: {stock.available_quantity}, Requested: {quantity}."
            )

        before_qty = stock.on_hand_quantity
        before_res = stock.reserved_quantity
        after_qty = before_qty - quantity

        stock.on_hand_quantity = after_qty
        stock.save()

        # Ledger transaction
        StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=warehouse,
            location=location,
            movement_type=movement_type,
            quantity=-quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            before_reserved=before_res,
            after_reserved=before_res,
            reference_type=reference_type,
            reference_id=str(reference_id),
            reason=reason or f"Direct stock deduction of {quantity} units",
            performed_by=performed_by
        )
        return stock

    @classmethod
    @transaction.atomic
    def reserve_stock(
        cls,
        product,
        warehouse,
        quantity: int,
        variant=None,
        location=None,
        reference_type='ORDER',
        reference_id='',
        performed_by=None,
        expires_at=None
    ) -> StockReservation:
        """
        Holds inventory for an order without deducting physical on-hand stock.
        Mathematical invariant:
            on_hand stays constant, reserved increases by quantity, available decreases by quantity.
        """
        if quantity <= 0:
            raise StockValidationError(f"Reservation quantity must be positive, got {quantity}.")

        stock = cls.get_or_create_stock(product, warehouse, variant=variant, location=location)

        # Row lock
        stock = Stock.objects.select_for_update().get(pk=stock.pk)

        if stock.available_quantity < quantity:
            sku = variant.sku if variant else (product.sku or product.title)
            raise InsufficientStockError(
                f"Cannot reserve {quantity} units for {sku}. Available stock is only {stock.available_quantity}."
            )

        before_qty = stock.on_hand_quantity
        before_res = stock.reserved_quantity
        after_res = before_res + quantity

        stock.reserved_quantity = after_res
        stock.save()

        # Create Reservation Record
        reservation = StockReservation.objects.create(
            stock=stock,
            quantity=quantity,
            reference_type=reference_type,
            reference_id=str(reference_id),
            status='PENDING',
            reserved_by=performed_by,
            expires_at=expires_at
        )

        # Record Reservation Movement
        StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=warehouse,
            location=location,
            movement_type='RESERVATION',
            quantity=quantity,
            before_quantity=before_qty,
            after_quantity=before_qty,
            before_reserved=before_res,
            after_reserved=after_res,
            reference_type=reference_type,
            reference_id=str(reference_id),
            reason=f"Hold {quantity} units for {reference_type} #{reference_id}",
            performed_by=performed_by
        )
        return reservation

    @classmethod
    @transaction.atomic
    def release_reservation(
        cls,
        reservation_or_id=None,
        reason='Order Cancelled',
        performed_by=None,
        reservation=None
    ) -> StockReservation:
        """
        Releases reserved inventory back to available pool upon order cancellation.
        Does NOT alter physical on-hand stock.
        """
        target = reservation if reservation is not None else reservation_or_id
        if isinstance(target, StockReservation):
            res_id = target.id
        else:
            res_id = target

        reservation = StockReservation.objects.select_for_update().get(pk=res_id)

        if reservation.status != 'PENDING':
            raise StockValidationError(f"Cannot release reservation with status '{reservation.status}'.")

        stock = Stock.objects.select_for_update().get(pk=reservation.stock_id)

        before_qty = stock.on_hand_quantity
        before_res = stock.reserved_quantity
        qty = reservation.quantity
        after_res = max(0, before_res - qty)

        stock.reserved_quantity = after_res
        stock.save()

        reservation.status = 'RELEASED'
        reservation.save()

        StockMovement.objects.create(
            product=stock.product,
            variant=stock.variant,
            warehouse=stock.warehouse,
            location=stock.location,
            movement_type='RESERVATION_RELEASE',
            quantity=qty,
            before_quantity=before_qty,
            after_quantity=before_qty,
            before_reserved=before_res,
            after_reserved=after_res,
            reference_type=reservation.reference_type,
            reference_id=reservation.reference_id,
            reason=reason or f"Released {qty} reserved units",
            performed_by=performed_by
        )
        return reservation

    @classmethod
    @transaction.atomic
    def fulfill_reservation(
        cls,
        reservation_or_id=None,
        reference_type='FULFILLMENT',
        reference_id='',
        performed_by=None,
        reservation=None
    ) -> StockReservation:
        """
        Converts a pending reservation into a completed sale deduction.
        Decreases physical on_hand AND decreases reserved_quantity by reservation.quantity.
        """
        target = reservation if reservation is not None else reservation_or_id
        if isinstance(target, StockReservation):
            res_id = target.id
        else:
            res_id = target

        reservation = StockReservation.objects.select_for_update().get(pk=res_id)

        if reservation.status != 'PENDING':
            raise StockValidationError(f"Cannot fulfill reservation with status '{reservation.status}'.")

        stock = Stock.objects.select_for_update().get(pk=reservation.stock_id)

        qty = reservation.quantity
        before_qty = stock.on_hand_quantity
        before_res = stock.reserved_quantity

        after_qty = max(0, before_qty - qty)
        after_res = max(0, before_res - qty)

        stock.on_hand_quantity = after_qty
        stock.reserved_quantity = after_res
        stock.save()

        reservation.status = 'FULFILLED'
        reservation.save()

        StockMovement.objects.create(
            product=stock.product,
            variant=stock.variant,
            warehouse=stock.warehouse,
            location=stock.location,
            movement_type='SALE',
            quantity=-qty,
            before_quantity=before_qty,
            after_quantity=after_qty,
            before_reserved=before_res,
            after_reserved=after_res,
            reference_type=reference_type or reservation.reference_type,
            reference_id=str(reference_id or reservation.reference_id),
            reason=f"Fulfilled reservation #{reservation.id} for {reservation.reference_type} #{reservation.reference_id}",
            performed_by=performed_by
        )
        return reservation

    @classmethod
    @transaction.atomic
    def adjust_stock(
        cls,
        stock_or_id=None,
        adjustment_type: str = 'SET',
        quantity: int = 0,
        reason: str = 'OTHER',
        notes: str = '',
        performed_by=None,
        stock=None,
        product=None,
        warehouse=None,
        variant=None,
        location=None
    ) -> StockAdjustment:
        """
        Performs a formal audited stock adjustment.
        Supported types:
          - 'INCREASE': on_hand += quantity
          - 'DECREASE': on_hand -= quantity
          - 'SET': on_hand = quantity
        """
        target = stock if stock is not None else stock_or_id
        if target is None:
            if product is not None and warehouse is not None:
                target = cls.get_or_create_stock(product, warehouse, variant=variant, location=location)
            else:
                raise StockValidationError("Must provide a Stock record or both Product and Warehouse.")

        if isinstance(target, Stock):
            stock_id = target.id
        else:
            stock_id = target

        stock = Stock.objects.select_for_update().get(pk=stock_id)

        prev_on_hand = stock.on_hand_quantity
        prev_res = stock.reserved_quantity

        if adjustment_type == 'INCREASE':
            if quantity <= 0:
                raise StockValidationError("Increase quantity must be greater than zero.")
            new_on_hand = prev_on_hand + quantity
            delta = quantity
            movement_type = 'ADJUSTMENT_IN'
        elif adjustment_type == 'DECREASE':
            if quantity <= 0:
                raise StockValidationError("Decrease quantity must be greater than zero.")
            if prev_on_hand - prev_res < quantity:
                raise InsufficientStockError(
                    f"Cannot decrease {quantity} units. Unreserved on-hand is only {prev_on_hand - prev_res}."
                )
            new_on_hand = prev_on_hand - quantity
            delta = -quantity
            if reason == 'DAMAGED':
                movement_type = 'DAMAGE'
            elif reason == 'LOST':
                movement_type = 'LOSS'
            else:
                movement_type = 'ADJUSTMENT_OUT'
        elif adjustment_type == 'SET':
            if quantity < 0:
                raise StockValidationError("Absolute stock count cannot be negative.")
            if quantity < prev_res:
                raise InsufficientStockError(
                    f"Cannot set on-hand to {quantity}. Currently reserved quantity is {prev_res}."
                )
            new_on_hand = quantity
            delta = new_on_hand - prev_on_hand
            movement_type = 'ADJUSTMENT_IN' if delta >= 0 else 'ADJUSTMENT_OUT'
        else:
            raise StockValidationError(f"Invalid adjustment type '{adjustment_type}'.")

        stock.on_hand_quantity = new_on_hand
        stock.save()

        adjustment = StockAdjustment.objects.create(
            stock=stock,
            adjustment_type=adjustment_type,
            quantity=quantity,
            previous_on_hand=prev_on_hand,
            new_on_hand=new_on_hand,
            reason=reason,
            notes=notes,
            adjusted_by=performed_by
        )

        StockMovement.objects.create(
            product=stock.product,
            variant=stock.variant,
            warehouse=stock.warehouse,
            location=stock.location,
            movement_type=movement_type,
            quantity=delta,
            before_quantity=prev_on_hand,
            after_quantity=new_on_hand,
            before_reserved=prev_res,
            after_reserved=prev_res,
            reference_type='ADJUSTMENT',
            reference_id=str(adjustment.id),
            reason=f"Stock adjustment: {reason}. {notes}".strip(),
            performed_by=performed_by
        )
        return adjustment

    @classmethod
    @transaction.atomic
    def transfer_stock(
        cls,
        product,
        source_warehouse,
        dest_warehouse,
        quantity: int,
        variant=None,
        source_location=None,
        dest_location=None,
        reason='',
        reference_id='',
        performed_by=None
    ) -> tuple[StockMovement, StockMovement]:
        """
        Moves physical units between two warehouses / locations atomically.
        """
        if quantity <= 0:
            raise StockValidationError(f"Transfer quantity must be positive, got {quantity}.")
        if source_warehouse.id == dest_warehouse.id and source_location == dest_location:
            raise StockValidationError("Source and destination warehouse/location cannot be identical.")

        # 1. Deduct from source
        src_stock = cls.get_or_create_stock(product, source_warehouse, variant=variant, location=source_location)
        src_stock = Stock.objects.select_for_update().get(pk=src_stock.pk)

        if src_stock.available_quantity < quantity:
            raise InsufficientStockError(
                f"Source warehouse {source_warehouse.code} has only {src_stock.available_quantity} available units."
            )

        src_before = src_stock.on_hand_quantity
        src_after = src_before - quantity
        src_res = src_stock.reserved_quantity
        src_stock.on_hand_quantity = src_after
        src_stock.save()

        out_movement = StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=source_warehouse,
            location=source_location,
            movement_type='TRANSFER_OUT',
            quantity=-quantity,
            before_quantity=src_before,
            after_quantity=src_after,
            before_reserved=src_res,
            after_reserved=src_res,
            reference_type='TRANSFER',
            reference_id=str(reference_id),
            reason=f"Transferred {quantity} units to {dest_warehouse.code}. {reason}".strip(),
            performed_by=performed_by
        )

        # 2. Add to destination
        dst_stock = cls.get_or_create_stock(product, dest_warehouse, variant=variant, location=dest_location)
        dst_stock = Stock.objects.select_for_update().get(pk=dst_stock.pk)

        dst_before = dst_stock.on_hand_quantity
        dst_after = dst_before + quantity
        dst_res = dst_stock.reserved_quantity
        dst_stock.on_hand_quantity = dst_after
        dst_stock.save()

        in_movement = StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=dest_warehouse,
            location=dest_location,
            movement_type='TRANSFER_IN',
            quantity=quantity,
            before_quantity=dst_before,
            after_quantity=dst_after,
            before_reserved=dst_res,
            after_reserved=dst_res,
            reference_type='TRANSFER',
            reference_id=str(reference_id),
            reason=f"Received {quantity} units from {source_warehouse.code}. {reason}".strip(),
            performed_by=performed_by
        )

        return out_movement, in_movement

    @classmethod
    def get_available_stock(cls, product, variant=None, warehouse=None) -> int:
        """
        Returns total immediately available stock across specified warehouse or all warehouses.
        """
        qs = Stock.objects.filter(product=product)
        if variant:
            qs = qs.filter(variant=variant)
        if warehouse:
            qs = qs.filter(warehouse=warehouse)
        return sum(s.available_quantity for s in qs)

    @classmethod
    def is_in_stock(cls, product, variant=None) -> bool:
        """Quick boolean helper to check if a product/variant is available for purchase."""
        return cls.get_available_stock(product, variant=variant) > 0

    @classmethod
    @transaction.atomic
    def purchase_product(
        cls,
        product,
        quantity: int = 1,
        variant=None,
        warehouse=None,
        reference_id='',
        performed_by=None
    ) -> Stock:
        """
        Deducts stock when a customer purchases a product.
        Finds the warehouse with available stock, locks the row using select_for_update,
        decreases stock atomically, updates status to OUT_OF_STOCK when 0, and records
        an immutable audit entry in StockMovement.
        """
        if quantity <= 0:
            raise StockValidationError(f"Purchase quantity must be positive, got {quantity}.")

        stocks_query = Stock.objects.select_for_update().filter(
            product=product,
            variant=variant,
        )
        if warehouse:
            stocks_query = stocks_query.filter(warehouse=warehouse)
        else:
            stocks_query = stocks_query.order_by('-warehouse__is_primary', '-on_hand_quantity')

        target_stock = None
        for s in stocks_query:
            if s.available_quantity >= quantity:
                target_stock = s
                break

        if not target_stock:
            available_total = sum(s.available_quantity for s in stocks_query)
            raise InsufficientStockError(
                f"Insufficient stock for '{product.title}'. Requested: {quantity}, Total available: {available_total}."
            )

        before_qty = target_stock.on_hand_quantity
        before_res = target_stock.reserved_quantity
        after_qty = before_qty - quantity

        target_stock.on_hand_quantity = after_qty
        target_stock.save()

        StockMovement.objects.create(
            product=product,
            variant=variant,
            warehouse=target_stock.warehouse,
            location=target_stock.location,
            movement_type='SALE',
            quantity=-quantity,
            before_quantity=before_qty,
            after_quantity=after_qty,
            before_reserved=before_res,
            after_reserved=before_res,
            reference_type='ORDER',
            reference_id=str(reference_id or f"ORD-{int(timezone.now().timestamp())}"),
            reason=f"Customer purchase of {quantity} unit(s)",
            performed_by=performed_by
        )
        return target_stock

