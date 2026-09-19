from .services import CartService


def cart_context(request):
    """
    Context processor injecting cart summary indicators into all storefront templates.
    Populates header cart badge count and total amount for both guests and authenticated users.
    """
    try:
        summary = CartService.get_cart_summary(request)
        return {
            'cart_item_count': summary['total_items'],
            'cart_total_price': f"{summary['total']:.2f}",
        }
    except Exception:
        return {
            'cart_item_count': 0,
            'cart_total_price': "0.00",
        }
