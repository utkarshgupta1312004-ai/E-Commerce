from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Order, DeliveryCheckpoint


def _can_access_order(request, order, allow_session: bool = False) -> bool:
    """
    Requirement 62: Customer Data Access Security.
    Evaluates whether the requesting user or session is authorized to view the order:
    1. Order customer owner (authenticated: order.user_id == request.user.id)
    2. Superuser or Django staff (admin audit)
    3. Department staff (orders, checkout, inventory, shipping)
    4. Browser session that just placed this checkout (allow_session=True only for success view)
    """
    if not order:
        return False
    if request.user.is_authenticated:
        if order.user_id == request.user.id:
            return True
        if request.user.is_superuser or request.user.is_staff:
            return True
        if hasattr(request.user, 'department_account'):
            dept_slug = getattr(request.user.department_account.department, 'slug', '')
            if dept_slug in ('orders', 'checkout', 'inventory', 'shipping'):
                return True
    session_dept = request.session.get('department_slug')
    if session_dept in ('orders', 'checkout', 'inventory', 'shipping'):
        return True
    if allow_session and request.session.get('last_order_number') == order.order_number:
        return True
    return False


def order_success_view(request, order_number):
    """
    Renders the order confirmation / success screen directly after placing a COD order.
    Authorizes customer owner, session order creator, and staff members.
    """
    order = Order.objects.filter(order_number__iexact=order_number).prefetch_related('items', 'checkpoints').first()
    if not order or not _can_access_order(request, order, allow_session=True):
        raise Http404(f"Order #{order_number} not found.")

    context = {
        'order': order,
        'items': order.items.all(),
        'checkpoints': order.checkpoints.filter(is_customer_visible=True),
    }
    return render(request, 'orders/order_success.html', context)


@login_required(login_url='accounts:login')
def order_list_view(request):
    """
    Customer portal 'My Orders' history screen (Requirements 50 & 62).
    Lists all orders placed by the current authenticated user in reverse chronological order.
    """
    orders = Order.objects.filter(user=request.user).prefetch_related('items', 'checkpoints').order_by('-created_at')
    context = {
        'orders': orders,
        'total_orders': orders.count(),
    }
    return render(request, 'orders/order_list.html', context)


def order_detail_view(request, order_number):
    """
    Customer detailed breakdown and live delivery tracking for a specific order (Requirements 50-66).
    Enforces strict ownership access control (Requirement 62).
    """
    order = Order.objects.filter(order_number__iexact=order_number).prefetch_related('items', 'checkpoints').first()
    if not order or not _can_access_order(request, order, allow_session=False):
        raise Http404(f"Order #{order_number} not found.")

    context = {
        'order': order,
        'items': order.items.all(),
        'checkpoints': order.checkpoints.filter(is_customer_visible=True).order_by('-timestamp'),
    }
    return render(request, 'orders/order_detail.html', context)


def order_receipt_view(request, order_number):
    """
    Clean, printable HTML receipt generated permanently from Order and OrderItem records.
    Contains print CSS rules (@media print) and window.print() trigger.
    Supports official Payment Receipt format (Requirement 60) via ?type=payment or when order is delivered & paid.
    Enforces strict ownership access control (Requirement 62).
    """
    order = Order.objects.filter(order_number__iexact=order_number).prefetch_related('items', 'checkpoints').first()
    if not order or not _can_access_order(request, order, allow_session=False):
        raise Http404(f"Order #{order_number} not found.")

    req_type = request.GET.get('type', '').strip().lower()
    is_payment_receipt = (req_type == 'payment') or (
        order.status == 'DELIVERED' and order.payment_status == 'PAID' and req_type != 'standard'
    )

    context = {
        'order': order,
        'items': order.items.all(),
        'checkpoints': order.checkpoints.filter(is_customer_visible=True),
        'is_payment_receipt': is_payment_receipt,
    }
    return render(request, 'orders/receipt.html', context)


@login_required(login_url='accounts:login')
def order_cancel_view(request, order_number):
    """
    Requirement 61: Customer Order Cancellation.
    Only allows cancellation according to valid order/shipping status (CONFIRMED / PENDING).
    Enforces strict ownership verification (Requirement 62).
    """
    order = get_object_or_404(Order, order_number__iexact=order_number)

    if order.user_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied("You can only cancel your own orders.")

    if request.method != 'POST':
        # Render cancellation confirmation warning
        return render(request, 'orders/order_cancel_confirm.html', {'order': order})

    if not order.can_cancel:
        messages.error(
            request,
            f"Order #{order.order_number} cannot be cancelled because it is already {order.customer_status_label.lower()}."
        )
        return redirect('orders:order_detail', order_number=order.order_number)

    order.status = 'CANCELLED'
    order.save(update_fields=['status', 'updated_at'])

    # Restore inventory stock if product is linked
    for item in order.items.all():
        if item.product:
            try:
                from apps.inventory.services import InventoryService
                from apps.inventory.models import Warehouse
                wh = Warehouse.objects.filter(is_primary=True).first() or Warehouse.objects.first()
                if wh:
                    stk = InventoryService.get_or_create_stock(item.product, wh, variant=item.variant)
                    stk.on_hand_quantity += item.quantity
                    stk.save(update_fields=['on_hand_quantity'])
            except Exception:
                pass

    # Log customer-visible DeliveryCheckpoint
    DeliveryCheckpoint.objects.create(
        order=order,
        status='CANCELLED',
        location=order.active_location_display,
        notes="Order cancelled by customer.",
        is_customer_visible=True
    )

    # Dispatch customer notification
    try:
        from apps.notifications.services import notify_order_event
        notify_order_event(order, 'ORDER_CANCELLED')
    except Exception:
        pass

    messages.success(request, f"Order #{order.order_number} has been cancelled successfully.")
    return redirect('orders:order_detail', order_number=order.order_number)


# ==============================================================================
# ORDER MANAGEMENT & ENTERPRISE CONSOLE VIEWS (matching inventory management style)
# ==============================================================================

from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


def _check_orders_access(request):
    """
    Validates access to the Orders Management Console:
    - Superuser
    - Session-authenticated staff for 'orders' department
    - User with view_order / change_order Django permissions
    """
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    if request.session.get('department_slug') == 'orders':
        return True
    if hasattr(request.user, 'department_account') and request.user.department_account.department.slug == 'orders':
        return True
    if request.user.has_perm('orders.view_order') or request.user.has_perm('orders.change_order'):
        return True
    return False


def _get_orders_staff_context(request, active_tab='dashboard'):
    """Common context dictionary for the enterprise orders console sidebar and header."""
    is_staff = _check_orders_access(request)
    dept_name = request.session.get('department_name', 'Order Fulfillment Hub')
    login_id = request.session.get('department_login_id', 'ORD-STAFF')
    operator_name = request.session.get('department_operator_name', '')

    total_orders = Order.objects.count()
    pending_cod = Order.objects.filter(payment_status='PENDING', payment_method='COD').count()
    confirmed_count = Order.objects.filter(status='CONFIRMED').count()

    return {
        'is_orders_staff': is_staff,
        'department_name': dept_name,
        'department_login_id': login_id,
        'department_operator_name': operator_name,
        'is_superadmin': request.user.is_authenticated and request.user.is_superuser,
        'active_tab': active_tab,
        'sidebar_total_orders': total_orders,
        'sidebar_pending_cod_count': pending_cod,
        'sidebar_confirmed_count': confirmed_count,
    }


def orders_management_dashboard_view(request):
    """
    Executive Order Command Center (/orders/manage/).
    Displays sales volume, COD pending amount, recent purchase orders, and fulfillment status.
    """
    if not _check_orders_access(request):
        messages.error(request, "Access restricted to Order Management Staff and Super Administrators.")
        return redirect('management:portal')

    context = _get_orders_staff_context(request, active_tab='dashboard')

    total_orders_count = Order.objects.count()
    confirmed_orders_count = Order.objects.filter(status='CONFIRMED').count()
    pending_cod_orders = Order.objects.filter(payment_status='PENDING', payment_method='COD')
    pending_cod_count = pending_cod_orders.count()
    pending_cod_amount = pending_cod_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0

    recent_orders = Order.objects.prefetch_related('items').order_by('-created_at')[:10]

    context.update({
        'total_orders_count': total_orders_count,
        'confirmed_orders_count': confirmed_orders_count,
        'pending_cod_count': pending_cod_count,
        'pending_cod_amount': pending_cod_amount,
        'total_revenue': total_revenue,
        'recent_orders': recent_orders,
    })
    return render(request, 'orders/manage/dashboard.html', context)


def orders_management_list_view(request):
    """
    Master Orders Directory (/orders/manage/all/).
    Faceted search, filter by order status, payment status, and pagination.
    """
    if not _check_orders_access(request):
        messages.error(request, "Access restricted to Order Management Staff and Super Administrators.")
        return redirect('management:portal')

    context = _get_orders_staff_context(request, active_tab='all_orders')

    queryset = Order.objects.prefetch_related('items').order_by('-created_at')

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(order_number__icontains=q) |
            Q(shipping_name__icontains=q) |
            Q(user__username__icontains=q) |
            Q(user__email__icontains=q) |
            Q(shipping_city__icontains=q) |
            Q(shipping_phone__icontains=q)
        )

    # Order status filter
    selected_status = request.GET.get('status', '').strip()
    if selected_status:
        queryset = queryset.filter(status=selected_status)

    # Payment status filter
    selected_payment_status = request.GET.get('payment_status', '').strip()
    if selected_payment_status:
        queryset = queryset.filter(payment_status=selected_payment_status)

    total_count = queryset.count()
    paginator = Paginator(queryset, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context.update({
        'page_obj': page_obj,
        'total_count': total_count,
        'q': q,
        'selected_status': selected_status,
        'selected_payment_status': selected_payment_status,
    })
    return render(request, 'orders/manage/order_list.html', context)


def orders_management_detail_view(request, order_number):
    """
    Enterprise Order Detail Inspection (/orders/manage/<order_number>/).
    """
    if not _check_orders_access(request):
        messages.error(request, "Access restricted to Order Management Staff and Super Administrators.")
        return redirect('management:portal')

    context = _get_orders_staff_context(request, active_tab='all_orders')
    order = get_object_or_404(Order.objects.prefetch_related('items'), order_number=order_number)

    context.update({
        'order': order,
        'items': order.items.all(),
    })
    return render(request, 'orders/manage/order_detail.html', context)


@require_POST
def orders_management_status_update_view(request, order_number):
    """
    Updates order status and payment status from the management console.
    """
    if not _check_orders_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    order = get_object_or_404(Order, order_number=order_number)
    new_status = request.POST.get('status', '').strip()
    new_payment_status = request.POST.get('payment_status', '').strip()

    valid_statuses = dict(Order.STATUS_CHOICES)
    valid_payments = dict(Order.PAYMENT_STATUS_CHOICES)

    updated = False
    status_changed = False
    payment_paid_now = False

    if new_status in valid_statuses and new_status != order.status:
        order.status = new_status
        status_changed = True
        updated = True
        if new_status == 'DELIVERED' and not order.delivered_at:
            order.delivered_at = timezone.now()

    if new_payment_status in valid_payments and new_payment_status != order.payment_status:
        if new_payment_status == 'PAID' and order.payment_status != 'PAID':
            payment_paid_now = True
        order.payment_status = new_payment_status
        updated = True

    if updated:
        order.save()

        if status_changed:
            DeliveryCheckpoint.objects.create(
                order=order,
                status=order.status,
                location=order.active_location_display,
                notes=f"Order status updated to {order.get_status_display()}",
                is_customer_visible=True
            )
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
                try:
                    from apps.notifications.services import notify_order_event
                    notify_order_event(order, event)
                except Exception:
                    pass

        if payment_paid_now:
            try:
                from apps.notifications.services import notify_order_event
                notify_order_event(order, 'COD_PAYMENT_RECEIVED')
            except Exception:
                pass

        messages.success(request, f"Order {order.order_number} status updated successfully ({order.status} / {order.payment_status}).")
    else:
        messages.info(request, "No changes were made to order status.")

    return redirect('orders:manage_detail', order_number=order_number)

