from typing import Any
import secrets
import string
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from .models import ManagementDepartment, DepartmentAccount
from .services.dashboard_metrics import get_superadmin_dashboard_metrics, format_currency_inr, format_currency_short


# Domain metadata enrichment for the Cartivo 20-app modular platform
DEPARTMENT_METADATA = {
    'accounts': {
        'phase': 'Phase 1',
        'category': 'Operations & Governance',
        'badge': 'Identity & RBAC',
        'capabilities': ['Custom User Model', 'Profile Details', 'Address Book', 'Role Enforcement'],
    },
    'settings': {
        'phase': 'Phase 1',
        'category': 'Operations & Governance',
        'badge': 'System Config',
        'capabilities': ['Currency Formats', 'Payment Toggles', 'Maintenance Mode', 'Notification Config'],
    },
    'audit': {
        'phase': 'Phase 1',
        'category': 'Operations & Governance',
        'badge': 'Security Logs',
        'capabilities': ['Staff Audit Trail', 'Login Activity', 'Critical State Mutations', 'Security Events'],
    },
    'catalog': {
        'phase': 'Phase 2',
        'category': 'Core Commerce',
        'badge': 'Taxonomy & Items',
        'capabilities': ['Hierarchical Categories', 'Product Variants (SKUs)', 'Brand Registry', 'WebP Media Pipeline'],
    },
    'inventory': {
        'phase': 'Phase 3',
        'category': 'Core Commerce',
        'badge': 'Stock & Warehouses',
        'capabilities': ['Multi-Warehouse Tracking', 'Atomic Stock Locking', 'Reserved Stock', 'Low-Stock Alerts'],
    },
    'search': {
        'phase': 'Phase 4',
        'category': 'Core Commerce',
        'badge': 'Discovery & Filters',
        'capabilities': ['Full-Text Search Index', 'Faceted Filtering', 'Search Analytics', 'Zero-Result Query Logs'],
    },
    'cms': {
        'phase': 'Phase 4',
        'category': 'Marketing & Engagement',
        'badge': 'Content & Banners',
        'capabilities': ['Flipkart Hero Carousel', 'Category Nav Items', 'Rich Page Editor', 'Announcement Bar'],
    },
    'wishlist': {
        'phase': 'Phase 5',
        'category': 'Core Commerce',
        'badge': 'Saved Items',
        'capabilities': ['One-Click Heart Toggle', 'Multiple Saved Lists', 'Move-to-Cart Action', 'Availability Sync'],
    },
    'cart': {
        'phase': 'Phase 6',
        'category': 'Core Commerce',
        'badge': 'Shopping Bag',
        'capabilities': ['Dual Guest/User Cart', 'Session-to-User Merge', 'Live Price & Tax Calc', 'Abandoned Cart Tracker'],
    },
    'promotions': {
        'phase': 'Phase 6',
        'category': 'Marketing & Engagement',
        'badge': 'Coupons & Deals',
        'capabilities': ['Coupon Code Engine', 'Fixed & Percentage Rules', 'Minimum Spend Limits', 'Redemption Tracking'],
    },
    'checkout': {
        'phase': 'Phase 7',
        'category': 'Core Commerce',
        'badge': 'Checkout Flow',
        'capabilities': ['Multi-Step Flow', 'Address Selection', 'Shipping Calculations', 'Idempotency Tokens'],
    },
    'payments': {
        'phase': 'Phase 7',
        'category': 'Payments & Fulfillment',
        'badge': 'Gateways & Webhooks',
        'capabilities': ['Stripe API & Elements', 'Razorpay SDK', 'Idempotent Webhooks', 'Automated Refund Pipeline'],
    },
    'orders': {
        'phase': 'Phase 8',
        'category': 'Payments & Fulfillment',
        'badge': 'Order Lifecycle',
        'capabilities': ['State Machine Transitions', 'Immutable Item Snapshots', 'ReportLab PDF Invoices', 'Customer Order History'],
    },
    'shipping': {
        'phase': 'Phase 8',
        'category': 'Payments & Fulfillment',
        'badge': 'Logistics & Zones',
        'capabilities': ['Carrier Rate Matrix', 'Tracking Dispatches', 'Shipping Zones', 'Delivery Status Updates'],
    },
    'fulfillment': {
        'phase': 'Phase 8',
        'category': 'Payments & Fulfillment',
        'badge': 'Warehouse Ops',
        'capabilities': ['Picking Lists', 'Packing Slips', 'Dispatch Batches', 'Fulfillment Queue Tracking'],
    },
    'notifications': {
        'phase': 'Phase 8',
        'category': 'Marketing & Engagement',
        'badge': 'Transactional Alerts',
        'capabilities': ['Async Celery Workers', 'Order Confirmations', 'Shipping Status Emails', 'Delivery Telemetry'],
    },
    'reviews': {
        'phase': 'Phase 9',
        'category': 'Marketing & Engagement',
        'badge': 'Ratings & Social Proof',
        'capabilities': ['Verified-Buyer Gating', '1-5 Star Ratings', 'Photo Attachments', 'Admin Moderation Queue'],
    },
    'recommendations': {
        'phase': 'Phase 9',
        'category': 'Marketing & Engagement',
        'badge': 'Personalization',
        'capabilities': ['Frequently Bought Together', 'Taxonomy Upsells', 'View-to-Cart Rules', 'Attributed Revenue'],
    },
    'analytics': {
        'phase': 'Phase 10',
        'category': 'Operations & Governance',
        'badge': 'Business Intelligence',
        'capabilities': ['Revenue & Sales Funnels', 'Average Order Value (AOV)', 'Customer Lifetime Value', 'Exportable Reports'],
    },
    'support': {
        'phase': 'Phase 10',
        'category': 'Operations & Governance',
        'badge': 'Helpdesk & Care',
        'capabilities': ['Customer Ticket Routing', 'Order-Linked Queries', 'Resolution Threads', 'Knowledge Base FAQs'],
    },
}


def management_page_view(request):
    """
    Dedicated Management Page View (/management/).
    Renders the unified enterprise operations overview for all 20 Cartivo domain services.
    If a Superadmin is authenticated, redirects directly to the Superadmin Dashboard.
    If CMS Department staff is authenticated, redirects directly to the CMS Dashboard.
    """
    # 1. Superadmin direct redirect to Superadmin Dashboard
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('management:dashboard')

    # 2. CMS / Accounts Department staff direct redirect to their respective Dashboards
    if request.session.get('department_slug') == 'cms':
        return redirect('cms:dashboard')
    if request.session.get('department_slug') == 'accounts':
        return redirect('accounts:dashboard')

    departments_qs = list(
        ManagementDepartment.objects.filter(is_active=True)
        .select_related('account')
        .order_by('display_order', 'name')
    )

    enriched_departments = []
    for dept in departments_qs:
        meta = DEPARTMENT_METADATA.get(dept.slug, {
            'phase': 'Foundation',
            'category': 'Core Platform',
            'badge': 'Domain Module',
            'capabilities': ['Model Definitions', 'Service Layer', 'Admin Console', 'API Endpoints'],
        })
        dept.phase = meta['phase']
        dept.domain_category = meta['category']
        dept.badge = meta['badge']
        dept.capabilities = meta['capabilities']
        
        # Account credentials state
        account = getattr(dept, 'account', None)
        if account:
            dept.has_account = True
            dept.account_status = account.status
            dept.account_login_id = account.login_id
        else:
            dept.has_account = False
            dept.account_status = DepartmentAccount.STATUS_PENDING
            dept.account_login_id = ''

        enriched_departments.append(dept)

    # Categories for interactive filtering
    categories = [
        {'id': 'all', 'name': 'All Domains', 'count': len(enriched_departments)},
        {'id': 'Core Commerce', 'name': 'Core Commerce', 'count': sum(1 for d in enriched_departments if d.domain_category == 'Core Commerce')},
        {'id': 'Payments & Fulfillment', 'name': 'Payments & Logistics', 'count': sum(1 for d in enriched_departments if d.domain_category == 'Payments & Fulfillment')},
        {'id': 'Marketing & Engagement', 'name': 'Marketing & CMS', 'count': sum(1 for d in enriched_departments if d.domain_category == 'Marketing & Engagement')},
        {'id': 'Operations & Governance', 'name': 'Operations & Admin', 'count': sum(1 for d in enriched_departments if d.domain_category == 'Operations & Governance')},
    ]

    is_superadmin = bool(request.user.is_authenticated and request.user.is_superuser)

    dept_session = None
    if request.session.get('department_account_id'):
        account_id = request.session.get('department_account_id')
        try:
            account = DepartmentAccount.objects.filter(
                id=account_id,
                status=DepartmentAccount.STATUS_ACTIVE
            ).select_related('department').first()
            if account:
                dept_session = {
                    'account_id': account.id,
                    'department_id': account.department.id,
                    'name': account.department.name,
                    'login_id': account.login_id,
                    'slug': account.department.slug,
                }
            else:
                request.session.pop('department_account_id', None)
                request.session.pop('department_id', None)
                request.session.pop('department_name', None)
                request.session.pop('department_login_id', None)
                request.session.pop('department_slug', None)
        except Exception:
            request.session.pop('department_account_id', None)
            request.session.pop('department_id', None)
            request.session.pop('department_name', None)
            request.session.pop('department_login_id', None)
            request.session.pop('department_slug', None)

    context = {
        'departments': enriched_departments,
        'total_departments': len(enriched_departments),
        'categories': categories,
        'is_superadmin': is_superadmin,
        'dept_session': dept_session,
    }
    return render(request, 'management/portal.html', context)


def superadmin_dashboard_view(request):
    """
    Dedicated Super Administrator Control Dashboard (/management/dashboard/).
    High-fidelity executive management dashboard computing real-time business intelligence
    across all 20 Cartivo domain services (sales, profit, COGS, inventory, carts, accounts).
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(
            request,
            "Access restricted. You must be authenticated as a Super Administrator to access the executive control dashboard."
        )
        return redirect(f"{reverse('management:login')}?next={reverse('management:dashboard')}")

    # Enriched Department Registry (All 20 Domains)
    departments_qs = list(ManagementDepartment.objects.filter(is_active=True).order_by('display_order', 'name'))
    enriched_departments = []
    for dept in departments_qs:
        meta = DEPARTMENT_METADATA.get(dept.slug, {
            'phase': 'Foundation',
            'category': 'Core Platform',
            'badge': 'Domain Module',
            'capabilities': ['Model Definitions', 'Service Layer', 'Admin Console', 'API Endpoints'],
        })
        dept.phase = meta['phase']
        dept.domain_category = meta['category']
        dept.badge = meta['badge']
        dept.capabilities = meta['capabilities']
        enriched_departments.append(dept)

    # Recent Audit & Security Activity
    recent_audit_logs = []
    try:
        from apps.audit.models import AuditLog
        recent_audit_logs = list(
            AuditLog.objects.select_related('user')
            .exclude(action__in=[
                'assistant_tool_search_products',
                'assistant_tool_filter_products',
                'assistant_tool_compare_products',
                'assistant_tool_get_product_features'
            ])
            .order_by('-timestamp')[:8]
        )
    except Exception:
        recent_audit_logs = []

    # Comprehensive live multi-app business intelligence
    metrics = get_superadmin_dashboard_metrics()

    context = {
        'departments': enriched_departments,
        'total_departments': len(enriched_departments),
        'recent_audit_logs': recent_audit_logs,
        'active_tab': 'dashboard',
        **metrics,
        # Executive Reference KPIs (dynamically bound to live metrics)
        'gross_target_val': metrics['gross_profit_display'],
        'target_percent': f"{metrics['profit_margin_pct']}%",
        'total_orders_val': str(metrics['total_orders_count']),
        'total_orders_change': f"{metrics['completed_orders_count']} delivered",
        'total_sales_val': metrics['gross_revenue_display'],
        'total_sales_change': f"{metrics['total_units_sold']} units sold",
        'total_visits_val': str(metrics['total_carts']),
        'total_visits_change': f"{metrics['cart_conversion_rate']}% conv",
        'bounce_rate_val': f"{metrics['cart_abandonment_rate']}%",
        'bounce_rate_change': 'abandoned',
        'monthly_revenue_kpi': metrics['monthly_run_rate_display'].replace('₹', ''),
        'yearly_revenue_kpi': metrics['yearly_run_rate_display'].replace('₹', ''),
    }
    return render(request, 'management/superadmin_dashboard.html', context)


def superadmin_sales_view(request):
    """
    Dedicated Superadmin Sales & Financial KPIs Console (/management/sales/).
    Real-time revenue metrics, financial KPIs, sales area trend curves, payment gateway routing,
    and filterable transactions ledger derived from live order & catalog data.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect(f"{reverse('management:login')}?next={reverse('management:sales')}")

    metrics = get_superadmin_dashboard_metrics()
    context = {
        'active_tab': 'sales',
        **metrics,
        'gross_revenue': metrics['gross_revenue_display'],
        'net_revenue': metrics['net_revenue_display'],
        'gross_profit': metrics['gross_profit_display'],
        'profit_margin': metrics['profit_margin_display'],
        'aov_val': metrics['aov_display'],
        'completed_orders_val': str(metrics['completed_orders_count']),
        'conversion_rate_val': metrics['cart_conversion_rate_display'],
        'refund_rate_val': f"{(metrics['cancelled_orders_count'] / metrics['total_orders_count'] * 100) if metrics['total_orders_count'] > 0 else 0.0:.1f}%",
    }
    return render(request, 'management/superadmin_sales.html', context)


def superadmin_analytics_view(request):
    """
    Dedicated Superadmin Graph Analyst & Deep Visual Analytics Console (/management/analytics/).
    Multi-metric comparative dual-bar charts, domain revenue donut ring, acquisition funnel cohorts,
    and regional/hardware telemetry.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect(f"{reverse('management:login')}?next={reverse('management:analytics')}")

    metrics = get_superadmin_dashboard_metrics()
    context = {
        'active_tab': 'analytics',
        **metrics,
        'monthly_analytics': metrics['monthly_analytics'],
        'monthly_revenue_kpi': metrics['monthly_run_rate_display'].replace('₹', ''),
        'yearly_revenue_kpi': metrics['yearly_run_rate_display'].replace('₹', ''),
    }
    return render(request, 'management/superadmin_analytics.html', context)


def superadmin_domains_view(request):
    """
    Dedicated Superadmin 20-Domains Infrastructure Console (/management/domains/).
    Complete micro-domains registry with status telemetry, development phase badges,
    app namespaces, and direct Django admin management links.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect(f"{reverse('management:login')}?next={reverse('management:domains')}")

    departments_qs = list(ManagementDepartment.objects.filter(is_active=True).order_by('display_order', 'name'))
    enriched_departments = []
    for dept in departments_qs:
        meta = DEPARTMENT_METADATA.get(dept.slug, {
            'phase': 'Foundation',
            'category': 'Core Platform',
            'badge': 'Domain Module',
            'capabilities': ['Model Definitions', 'Service Layer', 'Admin Console', 'API Endpoints'],
        })
        dept.phase = meta['phase']
        dept.domain_category = meta['category']
        dept.badge = meta['badge']
        dept.capabilities = meta['capabilities']
        enriched_departments.append(dept)

    context = {
        'active_tab': 'domains',
        'departments': enriched_departments,
        'total_departments': len(enriched_departments),
    }
    return render(request, 'management/superadmin_domains.html', context)


def superadmin_users_view(request):
    """
    Dedicated Superadmin Platform Accounts & User Directory (/management/users/).
    Searchable and filterable registry of all Superadmins, department staff, and shopper accounts.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect(f"{reverse('management:login')}?next={reverse('management:users')}")

    from django.contrib.auth import get_user_model
    User = get_user_model()

    total_users = User.objects.count()
    staff_count = User.objects.filter(is_staff=True).count()
    superuser_count = User.objects.filter(is_superuser=True).count()
    customer_count = max(0, total_users - staff_count)
    users_list = list(User.objects.all().order_by('-date_joined')[:50])

    context = {
        'active_tab': 'users',
        'total_users': total_users,
        'staff_count': staff_count,
        'superuser_count': superuser_count,
        'customer_count': customer_count,
        'users_list': users_list,
    }
    return render(request, 'management/superadmin_users.html', context)


def superadmin_login_view(request):
    """
    Dedicated Super Administrator Authentication View (/management/login/).
    Allows ONLY global Superadmin accounts (is_superuser=True) to authenticate.
    Upon successful login, ALWAYS directly redirects to the dedicated Superadmin Dashboard (/management/dashboard/).
    """
    # Direct redirect to admindash if already authenticated as superadmin
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('management:dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if not user.is_active:
                messages.error(request, "This account is deactivated.")
            elif not user.is_superuser:
                messages.error(
                    request, 
                    "Access restricted. Only Super Administrator credentials are authorized for this portal. Department staff credentials must be provisioned by the Superadmin."
                )
            else:
                login(request, user)
                request.session.cycle_key()
                # Session expires when browser/tab is closed
                request.session.set_expiry(0)
                messages.success(request, f"Welcome, Super Administrator {user.username}. Executive dashboard initialized.")
                # Direct redirect to Superadmin Dashboard (admindash)
                return redirect('management:dashboard')
        else:
            messages.error(request, "Invalid Superadmin credentials. Please verify your username and password.")

    return render(request, 'management/superadmin_login.html')


def superadmin_logout_view(request):
    """
    Super Administrator Logout View (/management/logout/).
    """
    if request.user.is_authenticated:
        logout(request)
    request.session.flush()
    messages.info(request, "Super Administrator session ended.")
    return redirect('management:portal')


# ==============================================================================
# DEPARTMENT ACCOUNTS & CREDENTIAL MANAGEMENT ENGINES
# ==============================================================================

def generate_suggested_login_id(dept: ManagementDepartment) -> str:
    """
    Generates a standardized, unique department login ID (e.g. 'CMS001', 'INV001', 'ACC001').
    """
    STANDARD_PREFIXES = {
        'cms': 'CMS',
        'inventory': 'INV',
        'accounts': 'ACC',
        'orders': 'ORD',
        'support': 'SUP',
        'catalog': 'CAT',
        'cart': 'CRT',
        'wishlist': 'WSH',
        'checkout': 'CHK',
        'payments': 'PAY',
        'shipping': 'SHP',
        'fulfillment': 'FUL',
        'promotions': 'PRO',
        'reviews': 'REV',
        'notifications': 'NOT',
        'recommendations': 'REC',
        'analytics': 'ANA',
        'audit': 'AUD',
        'settings': 'SET',
        'search': 'SRC',
    }
    prefix = STANDARD_PREFIXES.get(dept.slug, dept.code[:3].upper() if len(dept.code) >= 3 else 'DEP')
    if len(prefix) < 3:
        prefix = (prefix + 'DEP')[:3]

    counter = 1
    while True:
        candidate = f"{prefix}{counter:03d}"
        if not DepartmentAccount.objects.filter(login_id=candidate).exists():
            return candidate
        counter += 1


def generate_secure_password(length: int = 14) -> str:
    """
    Generates a cryptographically strong random password containing uppercase,
    lowercase, digits, and special characters.
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    pwd += [secrets.choice(chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(pwd)
    return ''.join(pwd)


def superadmin_department_accounts_view(request):
    """
    Super Administrator Department Accounts Management Console (/management/departments/accounts/).
    Provides full visibility into all 20 existing departments and their credential statuses.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect(f"{reverse('management:login')}?next={reverse('management:department_accounts')}")

    departments_qs = list(
        ManagementDepartment.objects.all().select_related('account').order_by('display_order', 'name')
    )

    enriched_departments = []
    for dept in departments_qs:
        meta = DEPARTMENT_METADATA.get(dept.slug, {
            'phase': 'Foundation',
            'category': 'Core Platform',
            'badge': 'Domain Module',
            'capabilities': ['Model Definitions', 'Service Layer', 'Admin Console'],
        })
        dept.phase = meta['phase']
        dept.domain_category = meta['category']
        dept.badge = meta['badge']

        # Determine account configuration state
        account = getattr(dept, 'account', None)
        if account:
            dept.has_account = True
            dept.account_status = account.status
            dept.login_id = account.login_id
            dept.last_login_display = account.last_login.strftime('%b %d, %Y %H:%M') if account.last_login else '—'
        else:
            dept.has_account = False
            dept.account_status = DepartmentAccount.STATUS_PENDING
            dept.login_id = '—'
            dept.last_login_display = '—'
            dept.suggested_login_id = generate_suggested_login_id(dept)

        enriched_departments.append(dept)

    total_departments = len(enriched_departments)
    configured_count = sum(1 for d in enriched_departments if d.has_account)
    active_count = sum(1 for d in enriched_departments if d.has_account and d.account_status == DepartmentAccount.STATUS_ACTIVE)
    suspended_count = sum(1 for d in enriched_departments if d.has_account and d.account_status == DepartmentAccount.STATUS_SUSPENDED)
    inactive_count = sum(1 for d in enriched_departments if d.has_account and d.account_status == DepartmentAccount.STATUS_INACTIVE)
    pending_count = sum(1 for d in enriched_departments if (not d.has_account) or d.account_status == DepartmentAccount.STATUS_PENDING)

    context = {
        'active_tab': 'dept_accounts',
        'departments': enriched_departments,
        'total_departments': total_departments,
        'configured_count': configured_count,
        'active_count': active_count,
        'suspended_count': suspended_count,
        'inactive_count': inactive_count,
        'pending_count': pending_count,
    }
    return render(request, 'management/superadmin_dept_accounts.html', context)


def superadmin_configure_department_account(request, dept_id: int):
    """
    Configures login credentials (Login ID, password, status) for an existing department.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect('management:login')

    dept = get_object_or_404(ManagementDepartment, id=dept_id)

    if request.method == 'POST':
        login_id = request.POST.get('login_id', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        status = request.POST.get('status', DepartmentAccount.STATUS_ACTIVE)

        if not login_id:
            messages.error(request, "Login ID is required.")
            return redirect('management:department_accounts')

        if DepartmentAccount.objects.filter(login_id=login_id).exclude(department=dept).exists():
            messages.error(request, f"Login ID '{login_id}' is already assigned to another department.")
            return redirect('management:department_accounts')

        if not password:
            messages.error(request, "Password is required to configure the account.")
            return redirect('management:department_accounts')

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect('management:department_accounts')

        if password != confirm_password:
            messages.error(request, "Password and Confirm Password do not match.")
            return redirect('management:department_accounts')

        if status not in [DepartmentAccount.STATUS_ACTIVE, DepartmentAccount.STATUS_SUSPENDED, DepartmentAccount.STATUS_INACTIVE, DepartmentAccount.STATUS_PENDING]:
            status = DepartmentAccount.STATUS_ACTIVE

        account, created = DepartmentAccount.objects.get_or_create(department=dept)
        account.login_id = login_id
        account.set_password(password)
        account.status = status
        account.save()
        account.sync_user(raw_password=password)

        messages.success(request, f"Login account for {dept.name} configured successfully with Login ID '{login_id}' [{status}].")

    return redirect('management:department_accounts')


def superadmin_edit_department_login_id(request, dept_id: int):
    """
    Updates the Login ID for a configured department account with uniqueness validation.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect('management:login')

    dept = get_object_or_404(ManagementDepartment, id=dept_id)
    account = getattr(dept, 'account', None)

    if not account:
        messages.error(request, f"No login account configured yet for {dept.name}. Please configure it first.")
        return redirect('management:department_accounts')

    if request.method == 'POST':
        login_id = request.POST.get('login_id', '').strip()
        if not login_id:
            messages.error(request, "Login ID cannot be empty.")
            return redirect('management:department_accounts')

        if DepartmentAccount.objects.filter(login_id=login_id).exclude(id=account.id).exists():
            messages.error(request, f"Login ID '{login_id}' is already in use by another department.")
            return redirect('management:department_accounts')

        account.login_id = login_id
        account.save(update_fields=['login_id', 'updated_at'])
        account.sync_user()
        messages.success(request, f"Login ID for {dept.name} updated to '{login_id}'.")

    return redirect('management:department_accounts')


def superadmin_reset_department_password(request, dept_id: int):
    """
    Resets the password for a department account. Never stores or reveals plaintext passwords.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect('management:login')

    dept = get_object_or_404(ManagementDepartment, id=dept_id)
    account = getattr(dept, 'account', None)

    if not account:
        messages.error(request, f"No login account configured yet for {dept.name}.")
        return redirect('management:department_accounts')

    if request.method == 'POST':
        new_password = request.POST.get('new_password') or request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not new_password:
            messages.error(request, "New password is required.")
            return redirect('management:department_accounts')

        if len(new_password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect('management:department_accounts')

        if new_password != confirm_password:
            messages.error(request, "New Password and Confirm Password do not match.")
            return redirect('management:department_accounts')

        account.set_password(new_password)
        account.save(update_fields=['password_hash', 'updated_at'])
        account.sync_user(raw_password=new_password)
        messages.success(request, f"Password for {dept.name} ({account.login_id}) has been reset successfully.")

    return redirect('management:department_accounts')


def superadmin_change_department_status(request, dept_id: int, new_status: str):
    """
    Quick status toggle (ACTIVE, SUSPENDED, INACTIVE) for a department account.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, "Access restricted to Super Administrators.")
        return redirect('management:login')

    dept = get_object_or_404(ManagementDepartment, id=dept_id)
    account = getattr(dept, 'account', None)

    if not account:
        messages.error(request, f"No login account configured yet for {dept.name}. Configure account first.")
        return redirect('management:department_accounts')

    new_status = new_status.upper()
    if new_status not in [DepartmentAccount.STATUS_ACTIVE, DepartmentAccount.STATUS_SUSPENDED, DepartmentAccount.STATUS_INACTIVE, DepartmentAccount.STATUS_PENDING]:
        messages.error(request, f"Invalid status: '{new_status}'.")
        return redirect('management:department_accounts')

    account.status = new_status
    account.save(update_fields=['status', 'updated_at'])
    account.sync_user()
    messages.success(request, f"Status for {dept.name} ({account.login_id}) updated to {new_status}.")
    return redirect('management:department_accounts')


def api_generate_department_credentials(request, dept_id: int):
    """
    JSON API for dynamic credential generation in modals.
    Returns a unique suggested Login ID and strong random password.
    """
    if not (request.user.is_authenticated and request.user.is_superuser):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    dept = get_object_or_404(ManagementDepartment, id=dept_id)
    suggested_id = generate_suggested_login_id(dept)
    password = generate_secure_password()

    return JsonResponse({
        'success': True,
        'department_name': dept.name,
        'login_id': suggested_id,
        'password': password
    })


def department_login_view(request):
    """
    Department Staff Authentication Endpoint (/management/department/login/).
    Authenticates Login ID and password, verifies account status, and gates access:
      - ACTIVE: Authenticates and updates last_login
      - SUSPENDED: Returns 'Your department account has been suspended. Please contact the Super Admin.'
      - INACTIVE: Returns 'Your department account is inactive. Please contact the Super Admin.'
      - PENDING: Returns 'Your department account is not active yet. Please contact the Super Admin.'
    """
    if request.method == 'POST':
        login_id = request.POST.get('login_id', '').strip()
        password = request.POST.get('password', '')

        if not login_id or not password:
            messages.error(request, "Please enter both Login ID and Password.")
            return redirect('management:portal')

        # Superadmins cannot log in as department staff
        if request.user.is_authenticated and request.user.is_superuser:
            messages.error(request, "Super Administrator accounts cannot log in as department staff. Please manage departments through the Superadmin Dashboard.")
            return redirect('management:portal')

        if User.objects.filter(username=login_id, is_superuser=True).exists():
            messages.error(request, "Super Administrator accounts cannot authenticate into department staff logins. Please sign in via the Superadmin Root Login.")
            return redirect('management:portal')

        # 1. Authenticate Credentials
        account = DepartmentAccount.objects.filter(login_id=login_id).select_related('department').first()

        if not account or not account.check_password(password):
            messages.error(request, "Invalid Department Login ID or Password.")
            return redirect('management:portal')

        # 2. Verify Account Status
        if account.status == DepartmentAccount.STATUS_ACTIVE:
            account.last_login = timezone.now()
            account.save(update_fields=['last_login'])

            # Synchronize linked Django user and log in via Django auth system
            user = account.sync_user(raw_password=password)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # Django auth-based login
            login(request, user)

            # Rotate session key to invalidate any browser-cached or stale session ID
            request.session.cycle_key()
            request.session.set_expiry(0)

            # Store department session
            request.session['department_account_id'] = account.id
            request.session['department_id'] = account.department.id
            request.session['department_name'] = account.department.name
            request.session['department_login_id'] = account.login_id
            request.session['department_slug'] = account.department.slug

            messages.success(request, f"Authenticated successfully as {account.department.name} ({account.login_id}).")

            # Route CMS / Accounts / Catalog / Inventory department to dedicated dashboards
            if account.department.slug == 'cms':
                return redirect('cms:dashboard')
            if account.department.slug == 'accounts':
                return redirect('accounts:dashboard')
            if account.department.slug == 'catalog':
                return redirect('catalog:dashboard')
            if account.department.slug == 'inventory':
                return redirect('inventory:dashboard')
            if account.department.slug == 'orders':
                return redirect('orders:manage_dashboard')
            if account.department.slug == 'checkout':
                return redirect('checkout:dashboard')

            return redirect(f"/management/#{account.department.slug}")

        elif account.status == DepartmentAccount.STATUS_SUSPENDED:
            messages.error(request, "Your department account has been suspended. Please contact the Super Admin.")
            return redirect('management:portal')

        elif account.status == DepartmentAccount.STATUS_INACTIVE:
            messages.error(request, "Your department account is inactive. Please contact the Super Admin.")
            return redirect('management:portal')

        elif account.status == DepartmentAccount.STATUS_PENDING:
            messages.error(request, "Your department account is not active yet. Please contact the Super Admin.")
            return redirect('management:portal')

        else:
            messages.error(request, "Your department account cannot be accessed. Please contact the Super Admin.")
            return redirect('management:portal')

    return redirect('management:portal')


def department_logout_view(request):
    """
    Department Staff Logout View (/management/department/logout/).
    """
    if request.user.is_authenticated:
        logout(request)
    request.session.flush()
    messages.info(request, "Department session ended.")
    return redirect('management:portal')


