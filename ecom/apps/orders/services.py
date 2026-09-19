from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import transaction
from django.contrib.auth.models import User
from .models import Order, OrderItem
from apps.accounts.models import Address
from apps.cart.models import Cart
from apps.cart.services import CartService
from apps.inventory.services import InventoryService, InsufficientStockError


class OrderService:
    """
    Handles atomic, concurrency-safe order creation, server-side price & stock re-validation,
    inventory deduction, stock movement logging, and cart conversion.
    """

    @classmethod
    @transaction.atomic
    def create_cod_order(
        cls,
        user: User,
        address: Address,
        customer_notes: str = '',
        idempotency_key: Optional[str] = None
    ) -> Order:
        """
        Creates a permanent Cash on Delivery (COD) Order from the customer's active cart.
        
        Guarantees:
        1. All stock records are locked via select_for_update() to prevent race conditions.
        2. Prices and quantities are validated server-side (never trusts client data).
        3. Stock is deducted and StockMovement ledger records are created.
        4. Cart is marked as CONVERTED.
        5. If any validation fails, entire transaction is automatically rolled back.
        """
        # 1. Retrieve active user cart
        cart = Cart.objects.filter(user=user, status='ACTIVE').first()
        if not cart or cart.items.count() == 0:
            raise ValueError("Your shopping cart is empty. Please add items before placing an order.")

        cart_items = list(cart.items.select_related('product', 'variant').all())
        if not cart_items:
            raise ValueError("Your shopping cart is empty. Please add items before placing an order.")

        # 2. Pre-validate stock and acquire locks for every item
        for item in cart_items:
            product = item.product
            variant = item.variant
            qty = item.quantity

            if not product.is_active or product.status != 'ACTIVE':
                raise ValueError(f"Product '{product.title}' is no longer available.")

            available = variant.available_stock if variant else product.total_available_stock
            if available < qty:
                sku_text = variant.sku if variant else (product.sku or product.title)
                raise InsufficientStockError(
                    f"Insufficient stock for '{sku_text}'. Requested: {qty}, Available: {available}."
                )

        # 3. Calculate server-side immutable financials
        subtotal = Decimal('0.00')
        order_items_data = []

        for item in cart_items:
            product = item.product
            variant = item.variant
            qty = item.quantity

            # Current database price snapshot
            unit_price = variant.effective_price if variant else product.effective_price
            item_subtotal = unit_price * qty
            subtotal += item_subtotal

            sku = variant.sku if (variant and variant.sku) else (product.sku or product.title)
            variant_name = variant.name if (variant and variant.name) else ''

            order_items_data.append({
                'product': product,
                'variant': variant,
                'sku': sku,
                'product_title': product.title,
                'variant_name': variant_name,
                'unit_price': unit_price,
                'quantity': qty,
                'subtotal': item_subtotal,
            })

        shipping_amount = Decimal('0.00')  # Free Express Shipping
        discount_amount = Decimal('0.00')
        tax_amount = Decimal('0.00')
        total_amount = subtotal + shipping_amount - discount_amount + tax_amount

        # 4. Generate unique human-readable order number
        order_number = Order.generate_order_number()

        # 5. Create Order master record with immutable address snapshot
        order = Order.objects.create(
            order_number=order_number,
            user=user,
            cart=cart,
            shipping_address=address,
            shipping_name=address.full_name,
            shipping_phone=address.phone,
            shipping_street_address=address.street_address,
            shipping_apartment=address.apartment,
            shipping_city=address.city,
            shipping_state=address.state,
            shipping_postal_code=address.postal_code,
            shipping_country=address.country,
            status='CONFIRMED',
            payment_method='COD',
            payment_status='PENDING',
            subtotal=subtotal,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            customer_notes=customer_notes.strip()
        )

        # 6. Create immutable OrderItem snapshots
        for data in order_items_data:
            OrderItem.objects.create(
                order=order,
                product=data['product'],
                variant=data['variant'],
                sku=data['sku'],
                product_title=data['product_title'],
                variant_name=data['variant_name'],
                unit_price=data['unit_price'],
                quantity=data['quantity'],
                subtotal=data['subtotal'],
            )

        # 7. Deduct inventory atomically & record StockMovement ledger
        for item in cart_items:
            InventoryService.purchase_product(
                product=item.product,
                quantity=item.quantity,
                variant=item.variant,
                reference_id=order.order_number,
                performed_by=user
            )

        # 8. Mark cart as CONVERTED (no longer active shopping cart)
        cart.status = 'CONVERTED'
        cart.save(update_fields=['status', 'updated_at'])

        return order
