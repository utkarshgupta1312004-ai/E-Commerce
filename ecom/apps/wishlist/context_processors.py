from .models import Wishlist


def wishlist_context(request):
    """
    Context processor injecting real-time wishlist indicators into all storefront templates.
    Populates header wishlist badge count for authenticated users (0 for guests).
    """
    try:
        if request.user.is_authenticated:
            wishlist = Wishlist.objects.filter(user=request.user, is_default=True).first()
            count = wishlist.items.count() if wishlist else 0
            return {
                'wishlist_item_count': count,
            }
        return {
            'wishlist_item_count': 0,
        }
    except Exception:
        return {
            'wishlist_item_count': 0,
        }
