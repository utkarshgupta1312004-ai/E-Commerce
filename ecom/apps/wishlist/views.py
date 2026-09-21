import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Wishlist, WishlistItem
from .services import WishlistService
from apps.catalog.models import Product, ProductVariant
from apps.cart.services import CartService


def _is_ajax(request) -> bool:
    """Helper determining if request is an XMLHttpRequest / Fetch JSON request."""
    return (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '') or
        request.content_type == 'application/json'
    )


@login_required(login_url='accounts:login')
def wishlist_view(request):
    """
    Renders the customer's dedicated Wishlist page (/wishlist/).
    Displays all saved products, variants, live Catalog prices, stock status,
    and actions to add/move items to the active shopping cart.
    """
    wishlist = WishlistService.get_or_create_wishlist(request.user)
    items = list(
        wishlist.items.select_related('product__category', 'product__brand', 'variant')
        .prefetch_related('product__images')
        .order_by('-created_at')
    )

    in_stock_count = sum(1 for item in items if item.is_in_stock)
    out_of_stock_count = len(items) - in_stock_count

    context = {
        'wishlist': wishlist,
        'items': items,
        'total_items': len(items),
        'in_stock_count': in_stock_count,
        'out_of_stock_count': out_of_stock_count,
    }
    return render(request, 'wishlist/wishlist_detail.html', context)


@require_POST
def toggle_wishlist_view(request):
    """
    Toggles a product/variant in the customer's wishlist.
    - If unauthenticated guest: redirects to login preserving ?next=, or returns JSON 401.
    - If authenticated customer: adds if absent, removes if present.
    """
    # 1. Unauthenticated guest redirect / 401 handling
    if not request.user.is_authenticated:
        next_url = request.META.get('HTTP_REFERER') or reverse('wishlist:wishlist_view')
        login_url = f"{reverse('accounts:login')}?next={next_url}"

        if _is_ajax(request):
            return JsonResponse({
                'success': False,
                'login_required': True,
                'login_url': login_url,
                'message': 'Please sign in to save products to your wishlist.'
            }, status=401)

        messages.info(request, "Please log in to save items to your wishlist.")
        return redirect(login_url)

    # 2. Extract product_id and optional variant_id
    product_id = None
    variant_id = None

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            variant_id = data.get('variant_id')
        except (ValueError, KeyError):
            return HttpResponseBadRequest("Invalid JSON payload.")
    else:
        product_id = request.POST.get('product_id')
        variant_id = request.POST.get('variant_id')

    if not product_id:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Missing product_id.'}, status=400)
        return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        if _is_ajax(request):
            return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
        messages.error(request, "Product not found.")
        return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))

    variant = None
    if variant_id:
        try:
            variant = ProductVariant.objects.get(id=variant_id, product=product)
        except ProductVariant.DoesNotExist:
            variant = None

    # 3. Perform toggle via service layer
    in_wishlist, total_items = WishlistService.toggle_wishlist(
        user=request.user,
        product=product,
        variant=variant
    )

    action_label = "Saved to" if in_wishlist else "Removed from"
    item_title = f"{product.title} ({variant.name})" if variant else product.title
    msg = f"'{item_title}' {action_label.lower()} your Wishlist."

    if _is_ajax(request):
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'total_items': total_items,
            'message': msg
        })

    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))


@require_POST
@login_required(login_url='accounts:login')
def remove_wishlist_item_view(request, item_id: int):
    """Removes a single item from the customer's wishlist."""
    success = WishlistService.remove_item_by_id(request.user, item_id)
    wishlist = WishlistService.get_or_create_wishlist(request.user)
    total_items = wishlist.total_items if wishlist else 0

    if _is_ajax(request):
        if success:
            return JsonResponse({
                'success': True,
                'total_items': total_items,
                'message': 'Item removed from your wishlist.'
            })
        return JsonResponse({'success': False, 'message': 'Item not found in your wishlist.'}, status=404)

    if success:
        messages.success(request, "Item removed from your wishlist.")
    else:
        messages.error(request, "Unable to find the specified item in your wishlist.")

    return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))


@require_POST
@login_required(login_url='accounts:login')
def add_to_cart_from_wishlist_view(request, item_id: int):
    """
    Adds a wishlist item to the active shopping bag without removing it from the wishlist.
    """
    success, msg = WishlistService.add_to_cart(request, item_id)
    cart_summary = CartService.get_cart_summary(request)

    if _is_ajax(request):
        return JsonResponse({
            'success': success,
            'message': msg,
            'cart_item_count': cart_summary['total_items'],
            'cart_total': f"{cart_summary['total']:.2f}",
        }, status=200 if success else 400)

    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))


@require_POST
@login_required(login_url='accounts:login')
def move_to_cart_view(request, item_id: int):
    """
    Moves a wishlist item to the shopping bag.
    Only removes from wishlist after cart addition has succeeded!
    """
    success, msg = WishlistService.move_to_cart(request, item_id)
    cart_summary = CartService.get_cart_summary(request)
    wishlist = WishlistService.get_or_create_wishlist(request.user)
    wishlist_total = wishlist.total_items if wishlist else 0

    if _is_ajax(request):
        return JsonResponse({
            'success': success,
            'message': msg,
            'wishlist_item_count': wishlist_total,
            'cart_item_count': cart_summary['total_items'],
            'cart_total': f"{cart_summary['total']:.2f}",
        }, status=200 if success else 400)

    if success:
        messages.success(request, msg)
    else:
        messages.error(request, msg)

    return redirect(request.META.get('HTTP_REFERER', 'wishlist:wishlist_view'))


@require_POST
@login_required(login_url='accounts:login')
def add_all_to_cart_view(request):
    """
    Adds all currently in-stock wishlist items to the active shopping bag.
    Unavailable or out-of-stock items remain in the wishlist.
    """
    res = WishlistService.add_all_to_cart(request)
    added = res['added_count']
    skipped = res['skipped_count']

    if added > 0:
        messages.success(request, f"{added} available item{'s' if added > 1 else ''} added to your bag.")
    if skipped > 0:
        messages.warning(request, f"{skipped} item{'s' if skipped > 1 else ''} could not be added due to out of stock status and remain in your wishlist.")
    if added == 0 and skipped == 0:
        messages.info(request, "Your wishlist is empty.")

    return redirect('cart:cart_detail' if added > 0 else 'wishlist:wishlist_view')


@require_POST
@login_required(login_url='accounts:login')
def clear_wishlist_view(request):
    """Clears all items from the customer's wishlist."""
    count = WishlistService.clear_wishlist(request.user)
    messages.success(request, f"Removed {count} item{'s' if count != 1 else ''} from your wishlist.")
    return redirect('wishlist:wishlist_view')
