import logging
from typing import Optional, Set, Tuple, Dict, Any
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction

from .models import Wishlist, WishlistItem
from apps.catalog.models import Product, ProductVariant
from apps.cart.services import CartService
from apps.inventory.services import InsufficientStockError

logger = logging.getLogger(__name__)


class WishlistService:
    """
    Business service layer managing customer Wishlist operations,
    atomic toggling, Cart transfers, and duplicate prevention.
    """

    @classmethod
    def get_or_create_wishlist(cls, user) -> Optional[Wishlist]:
        """Gets or creates the customer's primary wishlist."""
        if not user or not user.is_authenticated:
            return None
        return Wishlist.get_default_for_user(user)

    @classmethod
    def get_user_wishlist_product_ids(cls, user) -> Set[int]:
        """
        Returns a set of product IDs currently saved in the customer's wishlist.
        Single high-performance query used for storefront product card badge rendering.
        """
        if not user or not user.is_authenticated:
            return set()
        wishlist = Wishlist.get_default_for_user(user)
        if not wishlist:
            return set()
        return set(wishlist.items.values_list('product_id', flat=True))

    @classmethod
    def is_in_wishlist(cls, user, product: Product, variant: Optional[ProductVariant] = None) -> bool:
        """Checks whether a specific product or variant is saved in the user's wishlist."""
        if not user or not user.is_authenticated:
            return False
        wishlist = Wishlist.get_default_for_user(user)
        if not wishlist:
            return False
        qs = wishlist.items.filter(product=product)
        if variant:
            qs = qs.filter(variant=variant)
        return qs.exists()

    @classmethod
    def add_to_wishlist(
        cls,
        user,
        product: Product,
        variant: Optional[ProductVariant] = None
    ) -> Tuple[WishlistItem, bool]:
        """
        Adds a product/variant to the user's wishlist.
        Prevents duplicate entries via database get_or_create.
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to save items to wishlist.")

        wishlist = cls.get_or_create_wishlist(user)
        with transaction.atomic():
            item, created = WishlistItem.objects.get_or_create(
                wishlist=wishlist,
                product=product,
                variant=variant
            )
            if created:
                wishlist.save(update_fields=['updated_at'])
        return item, created

    @classmethod
    def remove_from_wishlist(
        cls,
        user,
        product_id: int,
        variant_id: Optional[int] = None
    ) -> bool:
        """Removes a product or variant from the customer's wishlist."""
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        wishlist = cls.get_or_create_wishlist(user)
        if not wishlist:
            return False

        qs = wishlist.items.filter(product_id=product_id)
        if variant_id is not None:
            qs = qs.filter(variant_id=variant_id)

        deleted_count, _ = qs.delete()
        if deleted_count > 0:
            wishlist.save(update_fields=['updated_at'])
            return True
        return False

    @classmethod
    def remove_item_by_id(cls, user, item_id: int) -> bool:
        """Removes a specific WishlistItem by its primary key, scoped to the requesting user."""
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        wishlist = cls.get_or_create_wishlist(user)
        if not wishlist:
            return False

        try:
            item = wishlist.items.get(id=item_id)
            item.delete()
            wishlist.save(update_fields=['updated_at'])
            return True
        except WishlistItem.DoesNotExist:
            return False

    @classmethod
    def toggle_wishlist(
        cls,
        user,
        product: Product,
        variant: Optional[ProductVariant] = None
    ) -> Tuple[bool, int]:
        """
        Toggles product/variant in the customer's wishlist.
        If already present, removes it.
        If absent, adds it.
        Returns: (is_now_in_wishlist: bool, current_total_items: int)
        """
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to update wishlist.")

        wishlist = cls.get_or_create_wishlist(user)
        qs = wishlist.items.filter(product=product)
        if variant:
            qs = qs.filter(variant=variant)

        existing = qs.first()
        if existing:
            existing.delete()
            wishlist.save(update_fields=['updated_at'])
            return False, wishlist.total_items
        else:
            WishlistItem.objects.create(
                wishlist=wishlist,
                product=product,
                variant=variant
            )
            wishlist.save(update_fields=['updated_at'])
            return True, wishlist.total_items

    @classmethod
    def add_to_cart(cls, request, wishlist_item_id: int) -> Tuple[bool, str]:
        """
        Adds a wishlist item to the active shopping cart while retaining it in the wishlist.
        Delegates validation and stock checking to CartService.
        """
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        wishlist = cls.get_or_create_wishlist(request.user)
        try:
            item = wishlist.items.select_related('product', 'variant').get(id=wishlist_item_id)
        except WishlistItem.DoesNotExist:
            return False, "Wishlist item not found."

        if not item.is_in_stock:
            return False, f"'{item.title}' is currently out of stock and cannot be added to cart."

        try:
            CartService.add_item(
                request=request,
                product=item.product,
                variant=item.variant,
                quantity=1
            )
            return True, f"'{item.title}' added to your shopping bag."
        except InsufficientStockError as e:
            return False, str(e)
        except Exception as e:
            logger.exception(f"Failed to add wishlist item #{wishlist_item_id} to cart")
            return False, f"Unable to add item to bag: {str(e)}"

    @classmethod
    def move_to_cart(cls, request, wishlist_item_id: int) -> Tuple[bool, str]:
        """
        Moves a wishlist item to the shopping cart.
        Crucial requirement: The item is ONLY deleted from the wishlist
        if adding to cart succeeds! If adding to cart fails, item remains saved in wishlist.
        """
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        wishlist = cls.get_or_create_wishlist(request.user)
        try:
            item = wishlist.items.select_related('product', 'variant').get(id=wishlist_item_id)
        except WishlistItem.DoesNotExist:
            return False, "Wishlist item not found."

        if not item.is_in_stock:
            return False, f"'{item.title}' is currently out of stock and cannot be moved to cart."

        try:
            with transaction.atomic():
                CartService.add_item(
                    request=request,
                    product=item.product,
                    variant=item.variant,
                    quantity=1
                )
                # Success! Now safely remove from wishlist
                item.delete()
                wishlist.save(update_fields=['updated_at'])
            return True, f"'{item.title}' moved to your shopping bag."
        except InsufficientStockError as e:
            return False, str(e)
        except Exception as e:
            logger.exception(f"Failed to move wishlist item #{wishlist_item_id} to cart")
            return False, f"Unable to move item to bag: {str(e)}"

    @classmethod
    def add_all_to_cart(cls, request) -> Dict[str, Any]:
        """
        Transfers all currently in-stock wishlist items into the customer's cart.
        Out-of-stock items remain safely in the wishlist.
        Returns detailed summary counts.
        """
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        wishlist = cls.get_or_create_wishlist(request.user)
        if not wishlist:
            return {'added_count': 0, 'skipped_count': 0, 'total_items': 0}

        items = list(wishlist.items.select_related('product', 'variant').all())
        added_count = 0
        skipped_count = 0

        for item in items:
            if not item.is_in_stock:
                skipped_count += 1
                continue
            try:
                CartService.add_item(
                    request=request,
                    product=item.product,
                    variant=item.variant,
                    quantity=1
                )
                added_count += 1
            except Exception as e:
                logger.warning(f"Could not add wishlist item #{item.id} to cart: {e}")
                skipped_count += 1

        return {
            'added_count': added_count,
            'skipped_count': skipped_count,
            'total_items': len(items)
        }

    @classmethod
    def clear_wishlist(cls, user) -> int:
        """Removes all items from the customer's default wishlist."""
        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required.")

        wishlist = cls.get_or_create_wishlist(user)
        if not wishlist:
            return 0
        deleted_count, _ = wishlist.items.all().delete()
        wishlist.save(update_fields=['updated_at'])
        return deleted_count
