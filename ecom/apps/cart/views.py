import json
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .services import CartService
from apps.catalog.models import Product, ProductVariant
from apps.inventory.services import InsufficientStockError


def cart_detail_view(request):
    """
    Renders shopping cart page for both guest session customers and logged-in users.
    Displays itemized products, variant tags, prices, quantity selectors, and totals.
    """
    summary = CartService.get_cart_summary(request)
    context = {
        'items': summary['items'],
        'total_items': summary['total_items'],
        'subtotal': summary['subtotal'],
        'shipping': summary['shipping'],
        'discount': summary['discount'],
        'tax': summary['tax'],
        'total': summary['total'],
        'is_empty': summary['is_empty'],
    }
    return render(request, 'cart/cart.html', context)


@require_POST
def add_to_cart_view(request):
    """
    Adds a product or variant to cart. Supports both standard form submissions
    and AJAX JSON calls from the storefront product detail page.
    """
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
        product_id = data.get('product_id')
        variant_id = data.get('variant_id')
        quantity = data.get('quantity', 1)
    else:
        product_id = request.POST.get('product_id')
        variant_id = request.POST.get('variant_id')
        quantity = request.POST.get('quantity', 1)

    try:
        quantity = max(1, int(quantity))
    except (ValueError, TypeError):
        quantity = 1

    product = get_object_or_404(Product, id=product_id, status='ACTIVE', visibility='PUBLIC', is_active=True)
    variant = None
    if variant_id:
        try:
            variant = ProductVariant.objects.filter(id=int(variant_id), product=product, is_active=True).first()
        except (ValueError, TypeError):
            variant = None

    try:
        item = CartService.add_item(request, product=product, variant=variant, quantity=quantity)
        summary = CartService.get_cart_summary(request)

        msg = f"Added {quantity}x '{item.title}' to your shopping bag."
        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': msg,
                'cart_item_count': summary['total_items'],
                'cart_total': f"{summary['total']:.2f}",
                'item_subtotal': f"{item.subtotal:.2f}",
                'item_quantity': item.quantity,
            })
        else:
            messages.success(request, msg)
            return redirect('cart:cart_detail')

    except InsufficientStockError as e:
        if is_ajax:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        messages.error(request, f"⚠️ {e}")
        return redirect('cart:cart_detail')
    except Exception as e:
        if is_ajax:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
        messages.error(request, f"⚠️ An unexpected error occurred: {e}")
        return redirect('cart:cart_detail')


@require_POST
def update_cart_view(request):
    """
    Updates item quantity in cart (+ / - / manual input).
    Returns updated subtotal, total, and counts via JSON for dynamic UI updates.
    """
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
        item_key = str(data.get('item_key', ''))
        quantity = data.get('quantity')
    else:
        item_key = str(request.POST.get('item_key', ''))
        quantity = request.POST.get('quantity')

    try:
        quantity = int(quantity)
    except (ValueError, TypeError):
        return HttpResponseBadRequest("Invalid quantity")

    try:
        updated_item = CartService.update_quantity(request, item_key=item_key, quantity=quantity)
        summary = CartService.get_cart_summary(request)

        if is_ajax:
            return JsonResponse({
                'success': True,
                'deleted': updated_item is None,
                'item_key': item_key,
                'item_quantity': updated_item.quantity if updated_item else 0,
                'item_subtotal': f"{updated_item.subtotal:.2f}" if updated_item else "0.00",
                'cart_item_count': summary['total_items'],
                'cart_total': f"{summary['total']:.2f}",
                'subtotal': f"{summary['subtotal']:.2f}",
                'is_empty': summary['is_empty'],
            })
        return redirect('cart:cart_detail')

    except InsufficientStockError as e:
        summary = CartService.get_cart_summary(request)
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': str(e),
                'cart_item_count': summary['total_items'],
                'cart_total': f"{summary['total']:.2f}",
            }, status=400)
        messages.warning(request, f"⚠️ {e}")
        return redirect('cart:cart_detail')


@require_POST
def remove_from_cart_view(request):
    """Removes a single line item from the shopping cart."""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'
    
    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except Exception:
            data = {}
        item_key = str(data.get('item_key', ''))
    else:
        item_key = str(request.POST.get('item_key', ''))

    removed = CartService.remove_item(request, item_key=item_key)
    summary = CartService.get_cart_summary(request)

    if is_ajax:
        return JsonResponse({
            'success': removed,
            'item_key': item_key,
            'cart_item_count': summary['total_items'],
            'cart_total': f"{summary['total']:.2f}",
            'subtotal': f"{summary['subtotal']:.2f}",
            'is_empty': summary['is_empty'],
        })
    messages.info(request, "Item removed from your bag.")
    return redirect('cart:cart_detail')


@require_POST
def clear_cart_view(request):
    """Empties the shopping cart completely."""
    CartService.clear_cart(request)
    messages.info(request, "Your shopping bag has been cleared.")
    return redirect('cart:cart_detail')
