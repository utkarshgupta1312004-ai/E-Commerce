from collections import defaultdict
from decimal import Decimal
import calendar
from typing import Dict, Any, List

from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.orders.models import Order, OrderItem
from apps.catalog.models import Product, Category, Brand
from apps.inventory.models import Warehouse, Stock
from apps.cart.models import Cart
from apps.core.models import ManagementDepartment


def format_currency_inr(amount: Decimal | float | int) -> str:
    """
    Formats amounts in Indian Rupee format or shorthand notation.
    e.g. 30294 -> '₹30,294', 10637060 -> '₹1.06 Cr', 150000 -> '₹1.50 L'
    """
    if amount is None:
        return '₹0'
    val = float(amount)
    if abs(val) >= 10000000:
        return f"₹{val / 10000000:.2f} Cr"
    elif abs(val) >= 100000:
        return f"₹{val / 100000:.2f} L"
    elif abs(val) >= 1000:
        return f"₹{val:,.2f}"
    return f"₹{val:.2f}"


def format_currency_short(amount: Decimal | float | int) -> str:
    """
    Shorthand format e.g. '₹30.3k', '₹1.06Cr'
    """
    if amount is None:
        return '₹0'
    val = float(amount)
    if abs(val) >= 10000000:
        return f"₹{val / 10000000:.2f}Cr"
    elif abs(val) >= 100000:
        return f"₹{val / 100000:.1f}L"
    elif abs(val) >= 1000:
        return f"₹{val / 1000:.1f}k"
    return f"₹{val:.0f}"


def get_superadmin_dashboard_metrics() -> Dict[str, Any]:
    """
    Core business intelligence aggregation engine for the Super Administrator Dashboard.
    Pulls, calculates, and correlates real-time metrics across:
    - apps.orders (Sales, revenue, order stages, cash collections, AOV, ledger)
    - apps.catalog + apps.orders (COGS, Gross Profit, Profit Margin %, top products, category breakdown)
    - apps.inventory (Warehouse stock, inventory valuation, stock alerts)
    - apps.cart (Active carts, conversion rate, abandonment rate)
    - apps.accounts + auth.User (User demographics, governance accounts)
    """
    User = get_user_model()
    now = timezone.now()

    # -------------------------------------------------------------
    # 1. Orders & Sales Intelligence (apps.orders)
    # -------------------------------------------------------------
    all_orders = Order.objects.all()
    valid_orders = all_orders.exclude(status='CANCELLED')

    total_orders_count = all_orders.count()
    completed_orders_count = all_orders.filter(status='DELIVERED').count()
    pending_orders_count = valid_orders.exclude(status='DELIVERED').count()
    cancelled_orders_count = all_orders.filter(status='CANCELLED').count()

    gross_revenue = sum((o.total_amount for o in valid_orders), Decimal('0.00'))
    delivered_revenue = sum((o.total_amount for o in all_orders.filter(status='DELIVERED')), Decimal('0.00'))
    total_discounts = sum((o.discount_amount for o in valid_orders), Decimal('0.00'))
    total_shipping_charges = sum((o.shipping_amount for o in valid_orders), Decimal('0.00'))
    net_revenue = gross_revenue - total_discounts

    aov = (gross_revenue / total_orders_count) if total_orders_count > 0 else Decimal('0.00')

    # COD Payments Breakdown
    cod_paid_amount = sum((o.total_amount for o in all_orders.filter(payment_method='COD', payment_status='PAID')), Decimal('0.00'))
    cod_pending_amount = sum((o.total_amount for o in all_orders.filter(payment_method='COD', payment_status='PENDING')), Decimal('0.00'))

    # Order Status Distribution
    status_counts = dict(all_orders.values('status').annotate(count=Count('id')).values_list('status', 'count'))

    # -------------------------------------------------------------
    # 2. Profitability & COGS (apps.orders + apps.catalog)
    # -------------------------------------------------------------
    total_cogs = Decimal('0.00')
    total_units_sold = 0
    category_revenue_map = defaultdict(lambda: {'revenue': Decimal('0.00'), 'units': 0, 'items_count': 0})
    product_performance_map = defaultdict(lambda: {
        'product_id': None,
        'title': '',
        'category': '',
        'units': 0,
        'revenue': Decimal('0.00'),
        'cogs': Decimal('0.00'),
        'image': '',
        'slug': '',
    })

    valid_order_items = OrderItem.objects.filter(order__in=valid_orders).select_related(
        'product', 'product__category', 'variant', 'order'
    )

    for item in valid_order_items:
        total_units_sold += item.quantity
        
        # Calculate item cost price
        if item.variant and item.variant.cost_price:
            cost = item.variant.cost_price
        elif item.product and item.product.cost_price:
            cost = item.product.cost_price
        else:
            cost = item.unit_price * Decimal('0.60')  # Default 60% baseline COGS if unset
            
        item_cogs = cost * item.quantity
        total_cogs += item_cogs

        # Category sales tracking
        cat_name = item.product.category.name if (item.product and item.product.category) else 'General'
        category_revenue_map[cat_name]['revenue'] += item.subtotal
        category_revenue_map[cat_name]['units'] += item.quantity
        category_revenue_map[cat_name]['items_count'] += 1

        # Product performance tracking
        key = item.product_id or item.product_title
        p = product_performance_map[key]
        p['product_id'] = item.product_id
        p['title'] = item.product_title
        p['category'] = cat_name
        p['units'] += item.quantity
        p['revenue'] += item.subtotal
        p['cogs'] += item_cogs
        if item.product:
            p['image'] = item.product.primary_image_url
            p['slug'] = item.product.slug

    gross_profit = gross_revenue - total_cogs
    profit_margin_pct = (gross_profit / gross_revenue * 100) if gross_revenue > 0 else Decimal('0.0')
    net_profit = gross_profit - total_discounts
    net_profit_margin_pct = (net_profit / gross_revenue * 100) if gross_revenue > 0 else Decimal('0.0')

    # Top performing products list
    top_products_list = []
    for p in product_performance_map.values():
        p_profit = p['revenue'] - p['cogs']
        p_margin = (p_profit / p['revenue'] * 100) if p['revenue'] > 0 else 0
        top_products_list.append({
            'product_id': p['product_id'],
            'title': p['title'],
            'category': p['category'],
            'units': p['units'],
            'revenue': p['revenue'],
            'revenue_display': format_currency_inr(p['revenue']),
            'profit': p_profit,
            'profit_display': format_currency_inr(p_profit),
            'margin': round(float(p_margin), 1),
            'image': p['image'],
            'slug': p['slug'],
        })
    top_products_list.sort(key=lambda x: x['revenue'], reverse=True)

    # Category breakdown formatting for Donut chart
    category_palette = [
        {'color': '#6366f1', 'bg': 'bg-indigo-500', 'name': 'Indigo'},
        {'color': '#ec4899', 'bg': 'bg-pink-500', 'name': 'Pink'},
        {'color': '#f59e0b', 'bg': 'bg-amber-500', 'name': 'Amber'},
        {'color': '#06b6d4', 'bg': 'bg-cyan-400', 'name': 'Cyan'},
        {'color': '#10b981', 'bg': 'bg-emerald-400', 'name': 'Emerald'},
        {'color': '#8b5cf6', 'bg': 'bg-purple-500', 'name': 'Purple'},
    ]
    category_breakdown: List[Dict[str, Any]] = []
    
    # SVG circle perimeter for r=62 is 2 * pi * 62 = ~389.55 -> ~390
    CIRCUMFERENCE = 390
    cumulative_offset = 0

    cat_items = sorted(category_revenue_map.items(), key=lambda x: x[1]['revenue'], reverse=True)
    for idx, (cat_name, data) in enumerate(cat_items):
        cat_rev = data['revenue']
        cat_pct = float((cat_rev / gross_revenue * 100) if gross_revenue > 0 else 0)
        style = category_palette[idx % len(category_palette)]
        
        dash_length = (cat_pct / 100.0) * CIRCUMFERENCE
        dash_offset = CIRCUMFERENCE - cumulative_offset
        cumulative_offset += dash_length

        category_breakdown.append({
            'name': cat_name,
            'revenue': cat_rev,
            'revenue_display': format_currency_inr(cat_rev),
            'units': data['units'],
            'percentage': round(cat_pct, 1),
            'color': style['color'],
            'bg': style['bg'],
            'stroke_dasharray': f"{round(dash_length, 1)} {round(CIRCUMFERENCE - dash_length, 1)}",
            'stroke_dashoffset': round(dash_offset, 1),
        })

    # Dominant category for donut center label
    primary_category = category_breakdown[0] if category_breakdown else {
        'name': 'Commerce',
        'percentage': 100.0,
        'revenue_display': format_currency_inr(gross_revenue),
    }

    # -------------------------------------------------------------
    # 3. Inventory & Warehouses (apps.inventory)
    # -------------------------------------------------------------
    all_warehouses = Warehouse.objects.filter(status='ACTIVE')
    stock_records = Stock.objects.select_related('product', 'variant', 'warehouse')

    total_units_on_hand = Stock.objects.aggregate(t=Sum('on_hand_quantity'))['t'] or 0
    total_units_reserved = Stock.objects.aggregate(t=Sum('reserved_quantity'))['t'] or 0
    low_stock_count = Stock.objects.filter(status='LOW_STOCK').count()
    out_of_stock_count = Stock.objects.filter(status='OUT_OF_STOCK').count()

    total_inventory_valuation = sum(
        (s.effective_cost_price * s.on_hand_quantity for s in stock_records),
        Decimal('0.00')
    )

    warehouse_breakdown = []
    for w in all_warehouses:
        w_units = w.total_units_on_hand
        w_val = w.total_inventory_value
        warehouse_breakdown.append({
            'id': w.id,
            'name': w.name,
            'code': w.code,
            'is_primary': w.is_primary,
            'units': w_units,
            'valuation': w_val,
            'valuation_display': format_currency_inr(w_val),
            'low_stock_count': w.low_stock_count,
            'out_of_stock_count': w.out_of_stock_count,
        })

    # -------------------------------------------------------------
    # 4. Shopping Cart & Conversion Funnel (apps.cart)
    # -------------------------------------------------------------
    all_carts = Cart.objects.all()
    total_carts = all_carts.count()
    active_carts = all_carts.filter(status='ACTIVE').count()
    converted_carts = all_carts.filter(status='CONVERTED').count()
    abandoned_carts = all_carts.filter(status='ABANDONED').count()

    cart_conversion_rate = (converted_carts / total_carts * 100) if total_carts > 0 else 0.0
    cart_abandonment_rate = (abandoned_carts / total_carts * 100) if total_carts > 0 else 0.0

    # -------------------------------------------------------------
    # 5. Catalog Summary (apps.catalog)
    # -------------------------------------------------------------
    total_products = Product.objects.filter(is_active=True).count()
    total_categories = Category.objects.filter(is_active=True).count()
    total_brands = Brand.objects.filter(is_active=True).count()

    # -------------------------------------------------------------
    # 6. Accounts & Governance Demographics (apps.accounts + auth)
    # -------------------------------------------------------------
    total_users = User.objects.count()
    staff_count = User.objects.filter(is_staff=True).count()
    superuser_count = User.objects.filter(is_superuser=True).count()
    customer_count = max(0, total_users - staff_count)

    # -------------------------------------------------------------
    # 7. Monthly Performance Analytics (Last 9 Months)
    # -------------------------------------------------------------
    monthly_analytics = []
    for i in range(8, -1, -1):
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        m_name = calendar.month_abbr[month]

        m_orders = Order.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).exclude(status='CANCELLED')

        m_sales = sum((o.total_amount for o in m_orders), Decimal('0.00'))
        m_count = m_orders.count()

        monthly_analytics.append({
            'month': m_name,
            'year': year,
            'sales_val': float(m_sales),
            'sales_k': round(float(m_sales) / 1000, 1),
            'sales_display': format_currency_short(m_sales),
            'orders': m_count,
        })

    max_m_sales = max((m['sales_val'] for m in monthly_analytics), default=1.0) or 1.0
    max_m_orders = max((m['orders'] for m in monthly_analytics), default=1) or 1

    for m in monthly_analytics:
        if m['sales_val'] > 0:
            m['sales_h'] = max(16, int((m['sales_val'] / max_m_sales) * 140))
        else:
            m['sales_h'] = 6
        if m['orders'] > 0:
            m['views_h'] = max(16, int((m['orders'] / max_m_orders) * 120))
        else:
            m['views_h'] = 8

    # Revenue Run-Rates
    current_month_sales = sum((o.total_amount for o in Order.objects.filter(
        created_at__year=now.year,
        created_at__month=now.month
    ).exclude(status='CANCELLED')), Decimal('0.00'))
    
    # If 0 in current month, fallback to gross revenue
    monthly_run_rate = current_month_sales if current_month_sales > 0 else gross_revenue
    annual_run_rate = monthly_run_rate * 12

    # -------------------------------------------------------------
    # 8. Live Recent Orders Ledger
    # -------------------------------------------------------------
    recent_orders = list(Order.objects.select_related('user').prefetch_related('items')[:6])

    # -------------------------------------------------------------
    # Context Aggregation
    # -------------------------------------------------------------
    return {
        # Financial & Profit KPIs
        'gross_revenue': gross_revenue,
        'gross_revenue_display': format_currency_inr(gross_revenue),
        'gross_revenue_short': format_currency_short(gross_revenue),
        'net_revenue': net_revenue,
        'net_revenue_display': format_currency_inr(net_revenue),
        'total_cogs': total_cogs,
        'total_cogs_display': format_currency_inr(total_cogs),
        'gross_profit': gross_profit,
        'gross_profit_display': format_currency_inr(gross_profit),
        'gross_profit_short': format_currency_short(gross_profit),
        'profit_margin_pct': round(float(profit_margin_pct), 1),
        'profit_margin_display': f"{profit_margin_pct:.1f}%",
        'net_profit': net_profit,
        'net_profit_display': format_currency_inr(net_profit),
        'net_profit_margin_pct': round(float(net_profit_margin_pct), 1),
        'aov': aov,
        'aov_display': format_currency_inr(aov),
        'total_discounts': total_discounts,
        'total_discounts_display': format_currency_inr(total_discounts),
        'cod_paid_amount': cod_paid_amount,
        'cod_paid_display': format_currency_inr(cod_paid_amount),
        'cod_pending_amount': cod_pending_amount,
        'cod_pending_display': format_currency_inr(cod_pending_amount),

        # Order Statistics
        'total_orders_count': total_orders_count,
        'completed_orders_count': completed_orders_count,
        'pending_orders_count': pending_orders_count,
        'cancelled_orders_count': cancelled_orders_count,
        'total_units_sold': total_units_sold,
        'recent_orders': recent_orders,
        'order_status_counts': status_counts,

        # Category & Products Intelligence
        'category_breakdown': category_breakdown,
        'primary_category': primary_category,
        'top_products': top_products_list[:5],
        'total_products': total_products,
        'total_categories': total_categories,
        'total_brands': total_brands,

        # Inventory Health
        'inventory_valuation': total_inventory_valuation,
        'inventory_valuation_display': format_currency_inr(total_inventory_valuation),
        'inventory_valuation_short': format_currency_short(total_inventory_valuation),
        'total_units_on_hand': total_units_on_hand,
        'total_units_reserved': total_units_reserved,
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'warehouse_breakdown': warehouse_breakdown,
        'warehouse_count': len(warehouse_breakdown),

        # Cart & Conversion Funnel
        'total_carts': total_carts,
        'active_carts': active_carts,
        'converted_carts': converted_carts,
        'abandoned_carts': abandoned_carts,
        'cart_conversion_rate': round(cart_conversion_rate, 1),
        'cart_conversion_rate_display': f"{cart_conversion_rate:.1f}%",
        'cart_abandonment_rate': round(cart_abandonment_rate, 1),

        # Users & Governance
        'total_users': total_users,
        'staff_count': staff_count,
        'superuser_count': superuser_count,
        'customer_count': customer_count,

        # Trend & Visuals
        'monthly_analytics': monthly_analytics,
        'monthly_run_rate_display': format_currency_inr(monthly_run_rate),
        'yearly_run_rate_display': format_currency_inr(annual_run_rate),
    }
