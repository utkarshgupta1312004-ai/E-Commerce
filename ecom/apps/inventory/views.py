from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from .models import Warehouse, Location, Stock, StockMovement, StockReservation, StockAdjustment
from .services import InventoryService, InsufficientStockError, StockValidationError
from .forms import StockAdjustmentForm, StockTransferForm
from apps.catalog.models import Product, Category


def _check_inventory_access(request):
    """
    Validates that user has access to Inventory Management Console:
    - Superuser
    - Session-authenticated staff for 'inventory' department
    - Linked user for inventory department (INV001)
    - User with view_stock / change_stock Django permissions
    - Staff user with inventory department role
    """
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    if request.session.get('department_slug') == 'inventory':
        return True
    if request.user.username == 'INV001':
        return True
    if hasattr(request.user, 'department_account') and request.user.department_account.department.slug == 'inventory':
        return True
    if request.user.has_perm('inventory.view_stock') or request.user.has_perm('inventory.change_stock'):
        return True
    return False


def _get_inventory_staff_context(request, active_tab='dashboard'):
    """Common context dictionary for the enterprise inventory console sidebar and header."""
    is_staff = _check_inventory_access(request)
    dept_name = request.session.get('department_name', 'Inventory & Warehouse Hub')
    login_id = request.session.get('department_login_id', 'INV-STAFF')
    operator_name = request.session.get('department_operator_name', '')

    try:
        total_stocks_count = Stock.objects.count()
        low_stock_count = Stock.objects.filter(status='LOW_STOCK').count()
        out_of_stock_count = Stock.objects.filter(status='OUT_OF_STOCK').count()
        warehouses_count = Warehouse.objects.filter(status='ACTIVE').count()
    except Exception:
        total_stocks_count = 0
        low_stock_count = 0
        out_of_stock_count = 0
        warehouses_count = 0

    return {
        'is_inventory_staff': is_staff,
        'department_name': dept_name,
        'department_login_id': login_id,
        'department_operator_name': operator_name,
        'is_superadmin': request.user.is_authenticated and request.user.is_superuser,
        'active_tab': active_tab,
        'sidebar_stock_count': total_stocks_count,
        'sidebar_low_stock_count': low_stock_count,
        'sidebar_out_of_stock_count': out_of_stock_count,
        'sidebar_warehouse_count': warehouses_count,
    }


def inventory_dashboard_view(request):
    """
    Executive Inventory Command Center.
    Presents stock level KPIs, valuation, low-stock triggers, out-of-stock items,
    recent audit movements, and multi-warehouse utilization.
    """
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted. You must be authenticated as an Inventory Manager or Superadmin.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='dashboard')

    # Aggregate KPIs
    stocks = Stock.objects.select_related('product', 'warehouse', 'variant')
    
    total_on_hand = stocks.aggregate(total=Sum('on_hand_quantity'))['total'] or 0
    total_reserved = stocks.aggregate(total=Sum('reserved_quantity'))['total'] or 0
    total_available = max(0, total_on_hand - total_reserved)
    
    unique_products_count = stocks.values('product_id').distinct().count()
    low_stock_items = stocks.filter(status='LOW_STOCK').order_by('on_hand_quantity')
    out_of_stock_items = stocks.filter(status='OUT_OF_STOCK').order_by('product__title')
    
    # Valuation calculation
    total_valuation = Decimal('0.00')
    for s in stocks.filter(on_hand_quantity__gt=0):
        try:
            total_valuation += Decimal(s.on_hand_quantity) * s.product.effective_price
        except Exception:
            pass

    # Warehouses breakdown
    warehouses = Warehouse.objects.filter(status='ACTIVE').annotate(
        stock_units=Sum('stock_records__on_hand_quantity'),
        stock_reserved=Sum('stock_records__reserved_quantity'),
        sku_count=Count('stock_records__id')
    )

    # Recent Audit movements
    recent_movements = StockMovement.objects.select_related(
        'product', 'variant', 'warehouse', 'performed_by'
    ).order_by('-created_at')[:10]

    context.update({
        'total_on_hand': total_on_hand,
        'total_reserved': total_reserved,
        'total_available': total_available,
        'unique_products_count': unique_products_count,
        'low_stock_count': low_stock_items.count(),
        'out_of_stock_count': out_of_stock_items.count(),
        'total_valuation': total_valuation,
        'low_stock_items': low_stock_items[:5],
        'out_of_stock_items': out_of_stock_items[:5],
        'warehouses': warehouses,
        'recent_movements': recent_movements,
    })
    return render(request, 'inventory/manage/dashboard.html', context)


def stock_list_view(request):
    """
    Comprehensive Stock Catalog Directory with real-time filtering,
    warehouse breakdowns, SKU search, and stock status filters.
    """
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted to authorized inventory personnel.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='stock')

    queryset = Stock.objects.select_related('product', 'warehouse', 'location', 'variant')

    # Filtering
    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(product__title__icontains=q) |
            Q(product__sku__icontains=q) |
            Q(variant__sku__icontains=q) |
            Q(variant__name__icontains=q) |
            Q(warehouse__name__icontains=q) |
            Q(warehouse__code__icontains=q)
        )

    warehouse_id = request.GET.get('warehouse', '').strip()
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    category_id = request.GET.get('category', '').strip()
    if category_id:
        queryset = queryset.filter(product__category_id=category_id)

    # Sorting
    sort = request.GET.get('sort', 'title')
    sort_mapping = {
        'title': 'product__title',
        '-title': '-product__title',
        'on_hand': 'on_hand_quantity',
        '-on_hand': '-on_hand_quantity',
        'status': 'status',
        'warehouse': 'warehouse__name',
    }
    order_by = sort_mapping.get(sort, 'product__title')
    queryset = queryset.order_by(order_by)

    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    warehouses_list = Warehouse.objects.filter(status='ACTIVE').order_by('name')
    categories_list = Category.objects.filter(is_active=True).order_by('name')

    context.update({
        'page_obj': page_obj,
        'stocks': page_obj.object_list,
        'total_count': paginator.count,
        'warehouses_list': warehouses_list,
        'categories_list': categories_list,
        'q': q,
        'selected_warehouse': warehouse_id,
        'selected_status': status_filter,
        'selected_category': category_id,
        'sort': sort,
    })
    return render(request, 'inventory/manage/stock_list.html', context)


def warehouse_list_view(request):
    """Lists all physical distribution facilities, hubs, and warehouses."""
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='warehouses')
    warehouses = Warehouse.objects.annotate(
        location_count=Count('locations', distinct=True),
        total_items=Sum('stock_records__on_hand_quantity'),
        total_reserved=Sum('stock_records__reserved_quantity'),
    ).order_by('-is_primary', 'name')

    context['warehouses'] = warehouses
    return render(request, 'inventory/manage/warehouse_list.html', context)


def warehouse_detail_view(request, pk):
    """Detailed view for a specific warehouse including internal storage locations and stock items."""
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='warehouses')
    warehouse = get_object_or_404(Warehouse, pk=pk)

    locations = warehouse.locations.all().order_by('code')
    stocks = warehouse.stock_records.select_related('product', 'location', 'variant').order_by('product__title')

    context.update({
        'warehouse': warehouse,
        'locations': locations,
        'stocks': stocks,
    })
    return render(request, 'inventory/manage/warehouse_detail.html', context)


def stock_movement_list_view(request):
    """
    Append-only Immutable Stock Movement Ledger.
    Allows auditing of every increase, decrease, sale, reservation, adjustment, and transfer.
    """
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='movements')

    queryset = StockMovement.objects.select_related(
        'product', 'variant', 'warehouse', 'location', 'performed_by'
    )

    q = request.GET.get('q', '').strip()
    if q:
        queryset = queryset.filter(
            Q(product__title__icontains=q) |
            Q(reference_id__icontains=q) |
            Q(reason__icontains=q) |
            Q(warehouse__name__icontains=q)
        )

    movement_type = request.GET.get('type', '').strip()
    if movement_type:
        queryset = queryset.filter(movement_type=movement_type)

    warehouse_id = request.GET.get('warehouse', '').strip()
    if warehouse_id:
        queryset = queryset.filter(warehouse_id=warehouse_id)

    queryset = queryset.order_by('-created_at')

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context.update({
        'page_obj': page_obj,
        'movements': page_obj.object_list,
        'movement_types': StockMovement.MOVEMENT_TYPE_CHOICES,
        'warehouses_list': Warehouse.objects.filter(status='ACTIVE'),
        'q': q,
        'selected_type': movement_type,
        'selected_warehouse': warehouse_id,
    })
    return render(request, 'inventory/manage/movement_list.html', context)


def stock_adjustment_view(request):
    """
    Audited manual stock reconciliation and adjustments (Cycle Counts, Damage, Expired, Found).
    """
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='adjustments')

    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            warehouse = form.cleaned_data['warehouse']
            qty = form.cleaned_data['quantity']
            adj_type = form.cleaned_data['adjustment_type']
            reason = form.cleaned_data['reason']
            notes = form.cleaned_data['notes']

            try:
                adjustment = InventoryService.adjust_stock(
                    product=product,
                    warehouse=warehouse,
                    adjustment_type=adj_type,
                    quantity=qty,
                    reason=reason,
                    notes=notes,
                    performed_by=request.user
                )
                messages.success(
                    request,
                    f"Stock adjustment successfully applied for '{product.title}' in {warehouse.code}. "
                    f"New balance: {adjustment.new_on_hand} units."
                )
                return redirect('inventory:stock_adjustments')
            except (InsufficientStockError, StockValidationError) as err:
                messages.error(request, f"Failed to execute adjustment: {err}")
    else:
        form = StockAdjustmentForm()

    recent_adjustments = StockAdjustment.objects.select_related(
        'stock__product', 'stock__warehouse', 'adjusted_by'
    ).order_by('-created_at')[:20]

    context.update({
        'form': form,
        'recent_adjustments': recent_adjustments,
    })
    return render(request, 'inventory/manage/adjustment_form.html', context)


def stock_transfer_view(request):
    """
    Facilitates transfer of physical stock between two active warehouses.
    """
    if not _check_inventory_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_inventory_staff_context(request, active_tab='transfers')

    if request.method == 'POST':
        form = StockTransferForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            source_wh = form.cleaned_data['source_warehouse']
            dest_wh = form.cleaned_data['dest_warehouse']
            qty = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            try:
                InventoryService.transfer_stock(
                    product=product,
                    source_warehouse=source_wh,
                    dest_warehouse=dest_wh,
                    quantity=qty,
                    reason=reason,
                    performed_by=request.user
                )
                messages.success(
                    request,
                    f"Successfully transferred {qty} units of '{product.title}' from {source_wh.code} to {dest_wh.code}."
                )
                return redirect('inventory:stock_list')
            except (InsufficientStockError, StockValidationError) as err:
                messages.error(request, f"Transfer rejected: {err}")
    else:
        form = StockTransferForm()

    context['form'] = form
    return render(request, 'inventory/manage/transfer_form.html', context)
