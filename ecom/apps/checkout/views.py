from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from apps.accounts.models import Address
from apps.cart.models import Cart
from apps.cart.services import CartService
from apps.orders.services import OrderService
from apps.inventory.services import InsufficientStockError
from apps.notifications.services import notify_order_event


@login_required(login_url='accounts:login')
def checkout_view(request):
    """
    Renders checkout page for authenticated customers.
    Merges any pending guest session items into user cart.
    Enforces server-side validation of stock and item availability.
    Only Cash on Delivery (COD) is active for payment.
    """
    # Defensive merge of session cart if any exists
    CartService.merge_guest_cart(request, request.user)

    cart = Cart.objects.filter(user=request.user, status='ACTIVE').first()
    if not cart or cart.items.count() == 0:
        messages.warning(request, "Your shopping bag is empty. Please add products before checking out.")
        return redirect('cart:cart_detail')

    cart_items = list(cart.items.select_related('product', 'variant', 'product__category').all())
    if not cart_items:
        messages.warning(request, "Your shopping bag is empty. Please add products before checking out.")
        return redirect('cart:cart_detail')

    # Pre-verify stock availability before rendering checkout
    out_of_stock_items = []
    for item in cart_items:
        avail = item.available_stock
        if avail < item.quantity:
            out_of_stock_items.append(f"{item.product.title} (Requested: {item.quantity}, In Stock: {avail})")

    if out_of_stock_items:
        messages.error(
            request,
            f"Some items in your cart have insufficient stock: {', '.join(out_of_stock_items)}. Please adjust quantities."
        )
        return redirect('cart:cart_detail')

    addresses = Address.objects.filter(user=request.user, address_type='shipping').order_by('-is_default', '-created_at')
    default_address = addresses.filter(is_default=True).first() or addresses.first()

    subtotal = cart.subtotal
    shipping = Decimal('0.00')
    discount = Decimal('0.00')
    tax = Decimal('0.00')
    total = subtotal + shipping - discount + tax

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'addresses': addresses,
        'default_address': default_address,
        'subtotal': subtotal,
        'shipping': shipping,
        'discount': discount,
        'tax': tax,
        'total': total,
        'total_items': cart.total_items,
    }
    return render(request, 'checkout/checkout.html', context)


@login_required(login_url='accounts:login')
@require_POST
def place_order_view(request):
    """
    Handles Cash on Delivery (COD) order placement.
    Atomically creates Order and OrderItems, locks and deducts stock,
    records StockMovement, and marks the cart as CONVERTED.
    """
    cart = Cart.objects.filter(user=request.user, status='ACTIVE').first()
    if not cart or cart.items.count() == 0:
        messages.error(request, "Your shopping bag is empty.")
        return redirect('cart:cart_detail')

    address_id = request.POST.get('address_id', '').strip()
    address = None

    # Option A: Selected existing address
    if address_id and address_id != 'new':
        try:
            address = Address.objects.filter(id=int(address_id), user=request.user).first()
        except (ValueError, TypeError):
            address = None

    # Option B: Entered a new address on checkout form
    if not address or address_id == 'new':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        street_address = request.POST.get('street_address', '').strip()
        apartment = request.POST.get('apartment', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        country = request.POST.get('country', 'United States').strip()
        save_address = request.POST.get('save_address') == 'on'

        if not (full_name and street_address and city and state and postal_code):
            messages.error(request, "Please fill in all required shipping address fields.")
            return redirect('checkout:checkout')

        address = Address(
            user=request.user,
            full_name=full_name,
            phone=phone,
            street_address=street_address,
            apartment=apartment,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            address_type='shipping',
            is_default=not Address.objects.filter(user=request.user, address_type='shipping').exists()
        )
        if save_address:
            address.save()

    payment_method = request.POST.get('payment_method', 'COD').upper()
    if payment_method != 'COD':
        messages.error(request, "Only Cash on Delivery (COD) is supported for this checkout.")
        return redirect('checkout:checkout')

    customer_notes = request.POST.get('customer_notes', '')

    try:
        order = OrderService.create_cod_order(
            user=request.user,
            address=address,
            customer_notes=customer_notes
        )
        # Store in session for immediate guest/user order confirmation access
        request.session['last_order_number'] = order.order_number

        # Initialize delivery tracking defaults and initial fulfillment checkpoint
        from apps.orders.models import DeliveryCheckpoint
        if not order.tracking_number:
            order.tracking_number = order.tracking_code
        if not order.current_location:
            order.current_location = 'Cartivo Central Fulfillment Hub'
        if not order.estimated_delivery_date:
            order.estimated_delivery_date = 'Within 3-5 Business Days'
        order.save(update_fields=['tracking_number', 'current_location', 'estimated_delivery_date'])

        if not order.checkpoints.exists():
            DeliveryCheckpoint.objects.create(
                order=order,
                status='CONFIRMED',
                location=order.current_location,
                notes='Order placed and confirmed via Cash on Delivery (COD)'
            )

        messages.success(request, f"🎉 Order {order.order_number} placed successfully!")
        return redirect('orders:order_success', order_number=order.order_number)

    except InsufficientStockError as e:
        messages.error(request, f"⚠️ Unable to place order due to stock shortage: {e}")
        return redirect('cart:cart_detail')
    except ValueError as e:
        messages.error(request, f"⚠️ {e}")
        return redirect('cart:cart_detail')
    except Exception as e:
        messages.error(request, f"⚠️ An unexpected error occurred while creating your order: {e}")
        return redirect('checkout:checkout')


# ==============================================================================
# CHECKOUT & DELIVERY MANAGEMENT CONSOLE (Department CHK001)
# ==============================================================================

from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from apps.orders.models import Order, DeliveryCheckpoint


def _check_checkout_access(request) -> bool:
    """
    Verifies staff authorization for Checkout & Delivery Management:
    - Super Administrator
    - Session department 'checkout' or 'orders'
    - DepartmentAccount assigned to 'checkout' or 'orders'
    - User with change_order permissions
    """
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    if request.session.get('department_slug') in ('checkout', 'orders'):
        return True
    if hasattr(request.user, 'department_account'):
        slug = getattr(request.user.department_account.department, 'slug', '')
        if slug in ('checkout', 'orders'):
            return True
    if request.user.is_staff:
        return True
    return False


def _get_checkout_staff_context(request, active_tab='dashboard') -> dict:
    """Common metadata and KPI counters for Checkout Operations console."""
    is_staff = _check_checkout_access(request)
    dept_name = request.session.get('department_name', 'Checkout & Logistics Command')
    login_id = request.session.get('department_login_id', 'CHK001')
    operator_name = request.session.get('department_operator_name', 'Lead Dispatch Controller')

    total_orders = Order.objects.count()
    out_for_delivery = Order.objects.filter(status='OUT_FOR_DELIVERY').count()
    in_transit = Order.objects.filter(status='SHIPPED').count()
    pending_cod = Order.objects.filter(payment_status='PENDING', payment_method='COD').count()
    delivered = Order.objects.filter(status='DELIVERED').count()

    return {
        'is_checkout_staff': is_staff,
        'department_name': dept_name,
        'department_login_id': login_id,
        'department_operator_name': operator_name,
        'is_superadmin': request.user.is_authenticated and request.user.is_superuser,
        'active_tab': active_tab,
        'sidebar_total_orders': total_orders,
        'sidebar_out_for_delivery': out_for_delivery,
        'sidebar_in_transit': in_transit,
        'sidebar_pending_cod': pending_cod,
        'sidebar_delivered': delivered,
    }


def checkout_dashboard_view(request):
    """
    Executive Checkout & Delivery Command Center (/checkout/dashboard/).
    Monitors live checkouts, delivery status pipelines, courier checkpoints, and COD collections.
    """
    if not _check_checkout_access(request):
        messages.error(request, "Access restricted to Checkout Operations Staff (CHK001) and Super Administrators.")
        return redirect('management:portal')

    context = _get_checkout_staff_context(request, active_tab='dashboard')

    total_orders = Order.objects.count()
    total_volume = Order.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Delivery status counts
    confirmed_count = Order.objects.filter(status='CONFIRMED').count()
    processing_count = Order.objects.filter(status='PROCESSING').count()
    shipped_count = Order.objects.filter(status='SHIPPED').count()
    out_for_delivery_count = Order.objects.filter(status='OUT_FOR_DELIVERY').count()
    delivered_count = Order.objects.filter(status='DELIVERED').count()
    cancelled_count = Order.objects.filter(status='CANCELLED').count()

    # Cash on Delivery Financials
    cod_orders = Order.objects.filter(payment_method='COD')
    cod_pending = cod_orders.filter(payment_status='PENDING')
    cod_collected = cod_orders.filter(payment_status='PAID')
    pending_cod_amount = cod_pending.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    collected_cod_amount = cod_collected.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Live Active Deliveries (needs attention or currently en-route)
    active_deliveries = Order.objects.filter(
        status__in=['CONFIRMED', 'PROCESSING', 'SHIPPED', 'OUT_FOR_DELIVERY']
    ).prefetch_related('items', 'checkpoints').order_by('-updated_at')[:8]

    # Recent completed checkouts
    recent_checkouts = Order.objects.prefetch_related('items', 'checkpoints').order_by('-created_at')[:10]

    carriers = [
        'Cartivo Express Delivery',
        'Blue Dart Express',
        'Delhivery Logistics',
        'Shadowfax Surface',
        'Ecom Express',
    ]

    context.update({
        'total_orders': total_orders,
        'total_volume': total_volume,
        'confirmed_count': confirmed_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'out_for_delivery_count': out_for_delivery_count,
        'delivered_count': delivered_count,
        'cancelled_count': cancelled_count,
        'cod_pending_count': cod_pending.count(),
        'pending_cod_amount': pending_cod_amount,
        'cod_collected_count': cod_collected.count(),
        'collected_cod_amount': collected_cod_amount,
        'active_deliveries': active_deliveries,
        'recent_checkouts': recent_checkouts,
        'carriers': carriers,
    })
    return render(request, 'checkout/manage/dashboard.html', context)


def checkout_deliveries_view(request):
    """
    Live Deliveries & Logistics Directory (/checkout/deliveries/).
    Search by order number, tracking number, customer, or destination city.
    Filter by delivery status, courier partner, and COD collection status.
    """
    if not _check_checkout_access(request):
        messages.error(request, "Access restricted to Checkout Operations Staff.")
        return redirect('management:portal')

    context = _get_checkout_staff_context(request, active_tab='deliveries')

    queryset = Order.objects.prefetch_related('items', 'checkpoints').order_by('-created_at')

    # Faceted search
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(order_number__icontains=q) |
            Q(tracking_number__icontains=q) |
            Q(shipping_name__icontains=q) |
            Q(shipping_city__icontains=q) |
            Q(current_location__icontains=q) |
            Q(delivery_partner__icontains=q) |
            Q(user__email__icontains=q)
        )

    # Status filter
    selected_status = request.GET.get('status', '').strip()
    if selected_status:
        queryset = queryset.filter(status=selected_status)

    # Carrier filter
    selected_carrier = request.GET.get('carrier', '').strip()
    if selected_carrier:
        queryset = queryset.filter(delivery_partner=selected_carrier)

    # Payment Status filter
    selected_payment = request.GET.get('payment_status', '').strip()
    if selected_payment:
        queryset = queryset.filter(payment_status=selected_payment)

    total_count = queryset.count()
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    carriers = Order.objects.values_list('delivery_partner', flat=True).distinct()
    carriers = [c for c in carriers if c]

    context.update({
        'page_obj': page_obj,
        'total_count': total_count,
        'q': q,
        'selected_status': selected_status,
        'selected_carrier': selected_carrier,
        'selected_payment': selected_payment,
        'carriers': carriers,
    })
    return render(request, 'checkout/manage/deliveries.html', context)


def checkout_delivery_detail_view(request, order_number):
    """
    In-Depth Delivery Dossier (/checkout/delivery/<order_number>/).
    Displays customer contact, full shipping address, parcel tracking code,
    step-by-step delivery progress, and historical checkpoint timeline.
    """
    if not _check_checkout_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_checkout_staff_context(request, active_tab='deliveries')
    order = get_object_or_404(
        Order.objects.prefetch_related('items', 'checkpoints'),
        order_number__iexact=order_number
    )

    carriers = [
        'Cartivo Express Delivery',
        'Blue Dart Express',
        'Delhivery Logistics',
        'Shadowfax Surface',
        'Ecom Express',
    ]

    context.update({
        'order': order,
        'items': order.items.all(),
        'checkpoints': order.checkpoints.all().order_by('-timestamp'),
        'carriers': carriers,
    })
    return render(request, 'checkout/manage/delivery_detail.html', context)


@require_POST
def checkout_delivery_update_view(request, order_number):
    """
    Updates delivery progress, courier partner, tracking number,
    physical checkpoint location, internal notes, and logs a timestamped DeliveryCheckpoint.
    Dispatches customer notifications via notify_order_event (Requirements 49, 58, 63, 64).
    """
    if not _check_checkout_access(request):
        messages.error(request, "Unauthorized.")
        return redirect('management:portal')

    order = get_object_or_404(Order, order_number__iexact=order_number)

    new_status = request.POST.get('status', '').strip()
    new_carrier = request.POST.get('delivery_partner', '').strip()
    new_tracking = request.POST.get('tracking_number', '').strip()
    new_tracking_url = request.POST.get('tracking_url', '').strip()
    new_location = request.POST.get('current_location', '').strip()
    new_eta = request.POST.get('estimated_delivery_date', '').strip()
    new_payment = request.POST.get('payment_status', '').strip()
    checkpoint_notes = request.POST.get('checkpoint_notes', '').strip()

    # Internal operational fields (Requirement 63)
    cod_collected_by = request.POST.get('cod_collected_by', '').strip()
    cod_received_amount = request.POST.get('cod_received_amount', '').strip()
    delivery_failure_reason = request.POST.get('delivery_failure_reason', '').strip()
    internal_notes = request.POST.get('internal_notes', '').strip()
    delivery_attempts = request.POST.get('delivery_attempts', '').strip()

    valid_statuses = dict(Order.STATUS_CHOICES)
    valid_payments = dict(Order.PAYMENT_STATUS_CHOICES)

    status_changed = False
    location_changed = False
    payment_paid_now = False

    if new_status in valid_statuses and new_status != order.status:
        old_status = order.status
        order.status = new_status
        status_changed = True
        if new_status == 'DELIVERED' and not order.delivered_at:
            order.delivered_at = timezone.now()

    if new_carrier:
        order.delivery_partner = new_carrier

    if new_tracking:
        order.tracking_number = new_tracking

    if new_tracking_url is not None:
        order.tracking_url = new_tracking_url

    if new_location and new_location != order.current_location:
        order.current_location = new_location
        location_changed = True

    if new_eta:
        order.estimated_delivery_date = new_eta

    if new_payment in valid_payments:
        if new_payment == 'PAID' and order.payment_status != 'PAID':
            payment_paid_now = True
        order.payment_status = new_payment

    if cod_collected_by:
        order.cod_collected_by = cod_collected_by

    if cod_received_amount:
        try:
            order.cod_received_amount = Decimal(cod_received_amount)
        except Exception:
            pass

    if delivery_failure_reason:
        order.delivery_failure_reason = delivery_failure_reason

    if internal_notes:
        order.internal_notes = internal_notes

    if delivery_attempts:
        try:
            order.delivery_attempts = int(delivery_attempts)
        except (ValueError, TypeError):
            pass

    order.save()

    # Automatically create delivery checkpoint log if status or location mutated, or note entered
    if status_changed or location_changed or checkpoint_notes:
        note = checkpoint_notes or f"Delivery status updated to {order.get_status_display()}"
        loc = order.current_location or order.active_location_display
        DeliveryCheckpoint.objects.create(
            order=order,
            status=order.status,
            location=loc,
            notes=note,
            is_customer_visible=True
        )

    # Trigger Customer Notifications (Requirement 58)
    if status_changed:
        event_map = {
            'READY_TO_PACK': 'ORDER_PACKED',
            'PACKED': 'ORDER_PACKED',
            'READY_TO_SHIP': 'ORDER_PACKED',
            'SHIPPED': 'ORDER_SHIPPED',
            'OUT_FOR_DELIVERY': 'OUT_FOR_DELIVERY',
            'DELIVERED': 'ORDER_DELIVERED',
            'FAILED': 'DELIVERY_FAILED',
            'RETURNED': 'ORDER_RETURNED',
            'CANCELLED': 'ORDER_CANCELLED',
        }
        event = event_map.get(order.status)
        if event:
            notify_order_event(order, event)

    if payment_paid_now:
        notify_order_event(order, 'COD_PAYMENT_RECEIVED')

    messages.success(
        request,
        f"✅ Delivery for #{order.order_number} updated: {order.get_status_display()} | Location: {order.current_location or 'N/A'}"
    )

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('checkout:delivery_detail', order_number=order.order_number)
