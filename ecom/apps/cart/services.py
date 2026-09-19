from decimal import Decimal
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import Cart, CartItem
from apps.catalog.models import Product, ProductVariant
from apps.inventory.services import InventoryService, InsufficientStockError


class CartItemWrapper:
    """
    Standardized cart item representation used by both session guest cart
    and database authenticated user cart.
    """
    def __init__(self, key: str, product: Product, variant: Optional[ProductVariant], quantity: int, db_item: Optional[CartItem] = None):
        self.key = str(key)
        self.id = db_item.id if db_item else key
        self.product = product
        self.variant = variant
        self.quantity = quantity
        self.db_item = db_item

    @property
    def unit_price(self) -> Decimal:
        if self.variant:
            return self.variant.effective_price
        return self.product.effective_price

    @property
    def subtotal(self) -> Decimal:
        return self.unit_price * self.quantity

    @property
    def sku(self) -> str:
        if self.variant and self.variant.sku:
            return self.variant.sku
        return self.product.sku or self.product.title

    @property
    def available_stock(self) -> int:
        if self.variant:
            return self.variant.available_stock
        return self.product.total_available_stock

    @property
    def is_in_stock(self) -> bool:
        return self.available_stock >= self.quantity

    @property
    def title(self) -> str:
        if self.variant and self.variant.name:
            return f"{self.product.title} ({self.variant.name})"
        return self.product.title

    @property
    def image_url(self) -> str:
        return self.product.primary_image_url


class CartService:
    """
    Unified cart service handling guest session carts, authenticated customer carts,
    stock validation, server-side totals calculation, and session-to-user cart merging.
    """

    @classmethod
    def get_or_create_user_cart(cls, user) -> Cart:
        """Retrieves or creates the active shopping cart for an authenticated user."""
        cart, _ = Cart.objects.get_or_create(user=user, status='ACTIVE')
        return cart

    @classmethod
    def _get_guest_cart_dict(cls, request) -> Dict[str, dict]:
        """Retrieves guest cart dictionary from the session."""
        if 'guest_cart' not in request.session:
            request.session['guest_cart'] = {}
        return request.session['guest_cart']

    @classmethod
    def add_item(cls, request, product: Product, variant: Optional[ProductVariant] = None, quantity: int = 1) -> CartItemWrapper:
        """
        Adds a product/variant to cart with server-side stock validation.
        Supports both guests (session) and authenticated users (database).
        """
        if quantity <= 0:
            quantity = 1

        # Check stock availability
        available = variant.available_stock if variant else product.total_available_stock
        if available <= 0:
            raise InsufficientStockError(f"'{product.title}' is currently out of stock.")

        if request.user.is_authenticated:
            cart = cls.get_or_create_user_cart(request.user)
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=variant,
                defaults={'quantity': 0}
            )
            new_qty = item.quantity + quantity
            if new_qty > available:
                new_qty = available
                if item.quantity >= available:
                    raise InsufficientStockError(f"Cannot add more units. Maximum available stock ({available}) already in cart.")
            item.quantity = new_qty
            item.save()
            return CartItemWrapper(key=str(item.id), product=product, variant=variant, quantity=item.quantity, db_item=item)
        else:
            if not request.session.session_key:
                request.session.create()
            guest_cart = cls._get_guest_cart_dict(request)
            key = f"{product.id}_{variant.id if variant else 0}"
            current_qty = guest_cart.get(key, {}).get('quantity', 0)
            new_qty = current_qty + quantity
            if new_qty > available:
                new_qty = available
                if current_qty >= available:
                    raise InsufficientStockError(f"Cannot add more units. Maximum available stock ({available}) already in cart.")
            
            guest_cart[key] = {
                'product_id': product.id,
                'variant_id': variant.id if variant else None,
                'quantity': new_qty,
            }
            request.session.modified = True
            return CartItemWrapper(key=key, product=product, variant=variant, quantity=new_qty)

    @classmethod
    def update_quantity(cls, request, item_key: str, quantity: int) -> Optional[CartItemWrapper]:
        """
        Updates quantity of a cart item. If quantity <= 0, deletes item.
        Validates stock availability server-side.
        """
        if request.user.is_authenticated:
            cart = cls.get_or_create_user_cart(request.user)
            try:
                item = CartItem.objects.select_related('product', 'variant').get(id=int(item_key), cart=cart)
            except (CartItem.DoesNotExist, ValueError):
                return None

            if quantity <= 0:
                item.delete()
                return None

            available = item.variant.available_stock if item.variant else item.product.total_available_stock
            if quantity > available:
                item.quantity = available
                item.save()
                raise InsufficientStockError(f"Only {available} item(s) available in stock. Quantity adjusted.")
            
            item.quantity = quantity
            item.save()
            return CartItemWrapper(key=str(item.id), product=item.product, variant=item.variant, quantity=item.quantity, db_item=item)
        else:
            guest_cart = cls._get_guest_cart_dict(request)
            if item_key not in guest_cart:
                return None

            if quantity <= 0:
                del guest_cart[item_key]
                request.session.modified = True
                return None

            entry = guest_cart[item_key]
            product = Product.objects.filter(id=entry['product_id']).first()
            if not product:
                del guest_cart[item_key]
                request.session.modified = True
                return None
            
            variant = None
            if entry.get('variant_id'):
                variant = ProductVariant.objects.filter(id=entry['variant_id']).first()

            available = variant.available_stock if variant else product.total_available_stock
            if quantity > available:
                guest_cart[item_key]['quantity'] = available
                request.session.modified = True
                raise InsufficientStockError(f"Only {available} item(s) available in stock. Quantity adjusted.")

            guest_cart[item_key]['quantity'] = quantity
            request.session.modified = True
            return CartItemWrapper(key=item_key, product=product, variant=variant, quantity=quantity)

    @classmethod
    def remove_item(cls, request, item_key: str) -> bool:
        """Removes a single item from the cart."""
        if request.user.is_authenticated:
            cart = cls.get_or_create_user_cart(request.user)
            try:
                deleted, _ = CartItem.objects.filter(id=int(item_key), cart=cart).delete()
                return deleted > 0
            except (ValueError, TypeError):
                return False
        else:
            guest_cart = cls._get_guest_cart_dict(request)
            if item_key in guest_cart:
                del guest_cart[item_key]
                request.session.modified = True
                return True
            return False

    @classmethod
    def clear_cart(cls, request) -> None:
        """Clears all items in current cart."""
        if request.user.is_authenticated:
            cart = cls.get_or_create_user_cart(request.user)
            cart.items.all().delete()
        else:
            request.session['guest_cart'] = {}
            request.session.modified = True

    @classmethod
    def get_cart_items(cls, request) -> List[CartItemWrapper]:
        """Returns standardized list of items in the current cart."""
        items: List[CartItemWrapper] = []

        if request.user.is_authenticated:
            cart = cls.get_or_create_user_cart(request.user)
            db_items = cart.items.select_related('product', 'variant', 'product__category').all()
            for db_item in db_items:
                items.append(CartItemWrapper(
                    key=str(db_item.id),
                    product=db_item.product,
                    variant=db_item.variant,
                    quantity=db_item.quantity,
                    db_item=db_item
                ))
        else:
            guest_cart = cls._get_guest_cart_dict(request)
            for key, entry in list(guest_cart.items()):
                product = Product.objects.filter(id=entry.get('product_id'), status='ACTIVE', visibility='PUBLIC').first()
                if not product:
                    # Clean dead product
                    del guest_cart[key]
                    request.session.modified = True
                    continue

                variant = None
                if entry.get('variant_id'):
                    variant = ProductVariant.objects.filter(id=entry.get('variant_id'), is_active=True).first()
                    if not variant:
                        del guest_cart[key]
                        request.session.modified = True
                        continue

                items.append(CartItemWrapper(
                    key=key,
                    product=product,
                    variant=variant,
                    quantity=entry.get('quantity', 1)
                ))

        return items

    @classmethod
    def get_cart_summary(cls, request) -> Dict[str, Any]:
        """Calculates server-side cart summary (subtotal, shipping, discount, grand total)."""
        items = cls.get_cart_items(request)
        total_items = sum(i.quantity for i in items)
        subtotal = sum((i.subtotal for i in items), Decimal('0.00'))
        
        # Complimentary Express Shipping policy
        shipping = Decimal('0.00')
        discount = Decimal('0.00')
        tax = Decimal('0.00')
        total = subtotal + shipping - discount + tax

        return {
            'items': items,
            'total_items': total_items,
            'subtotal': subtotal,
            'shipping': shipping,
            'discount': discount,
            'tax': tax,
            'total': total,
            'is_empty': len(items) == 0,
        }

    @classmethod
    def merge_guest_cart(cls, request, user) -> int:
        """
        Merges guest session cart into authenticated user's database cart upon login.
        If identical Product/Variant already exists in customer's cart, sums quantities
        up to available stock. Preserves all guest cart items.
        """
        guest_cart = request.session.get('guest_cart', {})
        if not guest_cart:
            return 0

        user_cart = cls.get_or_create_user_cart(user)
        merged_count = 0

        with transaction.atomic():
            for key, entry in guest_cart.items():
                product_id = entry.get('product_id')
                variant_id = entry.get('variant_id')
                qty = entry.get('quantity', 1)

                product = Product.objects.filter(id=product_id, status='ACTIVE').first()
                if not product:
                    continue

                variant = None
                if variant_id:
                    variant = ProductVariant.objects.filter(id=variant_id, is_active=True).first()

                available = variant.available_stock if variant else product.total_available_stock
                if available <= 0:
                    continue

                existing_item = CartItem.objects.filter(
                    cart=user_cart,
                    product=product,
                    variant=variant
                ).first()

                if existing_item:
                    combined_qty = existing_item.quantity + qty
                    existing_item.quantity = min(combined_qty, available)
                    existing_item.save()
                    merged_count += 1
                else:
                    save_qty = min(qty, available)
                    if save_qty > 0:
                        CartItem.objects.create(
                            cart=user_cart,
                            product=product,
                            variant=variant,
                            quantity=save_qty
                        )
                        merged_count += 1

            # Clear session cart after successful merge
            request.session['guest_cart'] = {}
            request.session.modified = True

        return merged_count
