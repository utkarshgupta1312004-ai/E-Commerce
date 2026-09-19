from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .services import CartService


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    """
    Automatically merges session-based guest cart into customer's database cart
    whenever a user authenticates (via login form, registration, or OAuth).
    """
    if request:
        try:
            CartService.merge_guest_cart(request, user)
        except Exception:
            pass
