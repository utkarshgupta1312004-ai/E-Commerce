from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import (
    NavbarItem,
    CategoryNavItem,
    PromoBanner,
    HomepageCategoryItem,
    TrustBadge,
    HomepageSection,
)


def home_view(request):
    """
    Render the Cartivo storefront homepage driven completely by CMS configurations.
    """
    now = timezone.now()

    # 1. Fetch active scheduled promotional banners
    active_banners = list(PromoBanner.objects.filter(
        is_active=True
    ).filter(
        Q(start_date__isnull=True) | Q(start_date__lte=now),
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).order_by('display_order', '-created_at'))

    # 2. Fetch active curated categories with catalog categories
    curated_categories = list(HomepageCategoryItem.objects.filter(
        is_active=True,
        category__is_active=True
    ).select_related('category').order_by('display_order', 'id'))

    # 3. Fetch active trust badges
    trust_badges = list(TrustBadge.objects.filter(
        is_active=True
    ).order_by('display_order', 'id'))

    # 4. Fetch category sub-menu items
    category_nav_items = list(CategoryNavItem.objects.filter(
        is_active=True
    ).select_related('category').order_by('display_order', 'id'))

    # 5. Fetch and orchestrate active homepage sections in display order
    sections_qs = HomepageSection.objects.filter(
        is_active=True
    ).order_by('display_order', 'id')

    resolved_sections = []
    for section in sections_qs:
        if section.section_type == 'category_bar':
            if category_nav_items:
                section.items = category_nav_items
                resolved_sections.append(section)

        elif section.section_type == 'hero_banners':
            if active_banners:
                section.items = active_banners
                resolved_sections.append(section)

        elif section.section_type == 'trust_bar':
            if trust_badges:
                section.items = trust_badges
                resolved_sections.append(section)

        elif section.section_type == 'curated_categories':
            if curated_categories:
                section.items = curated_categories
                resolved_sections.append(section)

        elif section.section_type == 'product_grid':
            products = list(section.get_products())
            if products:
                section.items = products
                resolved_sections.append(section)

        elif section.section_type in ('newsletter', 'custom_html'):
            section.items = []
            resolved_sections.append(section)

    context = {
        'sections': resolved_sections,
        'promo_banners': active_banners,
        'curated_categories': curated_categories,
        'trust_badges': trust_badges,
        'category_nav_items': category_nav_items,
    }
    return render(request, 'homepage.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from apps.catalog.models import Category


def _check_cms_access(request):
    try:
        if request.user.is_authenticated and request.user.is_superuser:
            return True

        dept_slug = request.session.get('department_slug')
        account_id = request.session.get('department_account_id')

        if dept_slug == 'cms' and account_id:
            from apps.core.models import DepartmentAccount
            account = DepartmentAccount.objects.filter(
                id=account_id,
                department__slug='cms',
                status=DepartmentAccount.STATUS_ACTIVE
            ).first()
            if account:
                return True

        return False
    except Exception:
        return False


def _get_cms_context_base(request, active_tab):
    is_cms_staff = bool(request.session.get('department_slug') == 'cms')
    is_superuser = bool(request.user.is_authenticated and request.user.is_superuser)

    all_banners_qs = PromoBanner.objects.all()
    all_sections_qs = HomepageSection.objects.all()
    all_nav_items_qs = CategoryNavItem.objects.all()
    all_curations_qs = HomepageCategoryItem.objects.all()
    all_trust_qs = TrustBadge.objects.all()
    all_navbar_qs = NavbarItem.objects.all()

    kpis = {
        'total_banners': all_banners_qs.count(),
        'active_banners': all_banners_qs.filter(is_active=True).count(),
        'total_sections': all_sections_qs.count(),
        'active_sections': all_sections_qs.filter(is_active=True).count(),
        'total_nav_items': all_nav_items_qs.count(),
        'active_nav_items': all_nav_items_qs.filter(is_active=True).count(),
        'total_curations': all_curations_qs.count(),
        'active_curations': all_curations_qs.filter(is_active=True).count(),
        'total_trust_badges': all_trust_qs.count(),
        'total_navbar_items': all_navbar_qs.count(),
    }

    dept_info = {
        'is_cms_staff': is_cms_staff,
        'is_superuser': is_superuser,
        'login_id': request.session.get('department_login_id', 'CMS001' if is_cms_staff else 'SUPERADMIN'),
        'dept_name': request.session.get('department_name', 'Content Management System (CMS)'),
        'operator_name': request.user.username if is_superuser else request.session.get('department_login_id', 'CMS Staff'),
    }

    return {
        'active_tab': active_tab,
        'kpis': kpis,
        'dept_info': dept_info,
    }


def cms_dashboard_view(request):
    """
    Dedicated Executive Dashboard for CMS Department (/cms/dashboard/).
    """
    if not _check_cms_access(request):
        messages.error(request, "Access restricted. Please sign in with CMS Department credentials or as a Super Administrator.")
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'dashboard')
    now = timezone.now()

    all_banners = list(PromoBanner.objects.all().order_by('display_order', '-created_at'))
    for b in all_banners:
        if not b.is_active:
            b.status_badge = 'Inactive'
            b.status_color = 'slate'
        elif b.start_date and now < b.start_date:
            b.status_badge = 'Scheduled'
            b.status_color = 'blue'
        elif b.end_date and now > b.end_date:
            b.status_badge = 'Expired'
            b.status_color = 'rose'
        else:
            b.status_badge = 'Live'
            b.status_color = 'emerald'

    context.update({
        'banners': all_banners,
        'category_nav_items': list(CategoryNavItem.objects.all().select_related('category').order_by('display_order', 'id')),
        'homepage_sections': list(HomepageSection.objects.all().order_by('display_order', 'id')),
        'curated_categories': list(HomepageCategoryItem.objects.all().select_related('category').order_by('display_order', 'id')),
        'trust_badges': list(TrustBadge.objects.all().order_by('display_order', 'id')),
        'navbar_items': list(NavbarItem.objects.all().select_related('parent').prefetch_related('children').order_by('display_order', 'id')),
        'catalog_categories': list(Category.objects.filter(is_active=True).order_by('name')),
        'root_navbar_items': list(NavbarItem.objects.filter(parent__isnull=True).order_by('display_order', 'title')),
        'section_types': HomepageSection.SECTION_TYPES,
        'filter_types': HomepageSection.FILTER_TYPES,
    })
    return render(request, 'cms/dashboard.html', context)


# ==============================================================================
# 1. HERO & PROMOTIONAL BANNERS
# ==============================================================================
def cms_banners_view(request):
    if not _check_cms_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'banners')
    now = timezone.now()
    qs = PromoBanner.objects.all().order_by('display_order', '-created_at')

    # Status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    # Time filter
    time_filter = request.GET.get('time', 'all')
    if time_filter == 'upcoming':
        qs = qs.filter(start_date__gt=now)
    elif time_filter == 'active_window':
        qs = qs.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
    elif time_filter == 'expired':
        qs = qs.filter(end_date__lt=now)

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(subtitle__icontains=q) | Q(badge_text__icontains=q) | Q(price_tag__icontains=q))

    banners = list(qs)
    for b in banners:
        if not b.is_active:
            b.status_badge = 'Inactive'
            b.status_color = 'slate'
        elif b.start_date and now < b.start_date:
            b.status_badge = 'Scheduled'
            b.status_color = 'blue'
        elif b.end_date and now > b.end_date:
            b.status_badge = 'Expired'
            b.status_color = 'rose'
        else:
            b.status_badge = 'Live'
            b.status_color = 'emerald'

    context.update({
        'banners': banners,
        'status_filter': status_filter,
        'time_filter': time_filter,
        'search_query': q,
        'total_count': len(banners),
    })
    return render(request, 'cms/banners.html', context)


def cms_banner_add_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Banner Title is required.")
            return redirect('cms:banners')

        uploaded_image = request.FILES.get('image')
        banner = PromoBanner.objects.create(
            title=title,
            subtitle=request.POST.get('subtitle', '').strip(),
            price_tag=request.POST.get('price_tag', '').strip(),
            badge_text=request.POST.get('badge_text', '').strip(),
            button_text=request.POST.get('button_text', 'Shop Now').strip(),
            button_url=request.POST.get('button_url', '/products/').strip(),
            bg_gradient=request.POST.get('bg_gradient', 'from-neutral-950 via-slate-900 to-neutral-950').strip(),
            border_color=request.POST.get('border_color', 'border-slate-800/80').strip(),
            text_color_theme=request.POST.get('text_color_theme', 'dark'),
            start_date=request.POST.get('start_date') or None,
            end_date=request.POST.get('end_date') or None,
            is_active=bool(request.POST.get('is_active')),
            display_order=int(request.POST.get('display_order', 0) or 0),
            image=uploaded_image if uploaded_image else None,
            image_url=request.POST.get('image_url', '').strip(),
        )
        messages.success(request, f"Banner '{banner.title}' created successfully.")
    return redirect('cms:banners')


def cms_banner_edit_view(request, banner_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    banner = get_object_or_404(PromoBanner, id=banner_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Banner Title is required.")
        else:
            banner.title = title
            banner.subtitle = request.POST.get('subtitle', '').strip()
            banner.price_tag = request.POST.get('price_tag', '').strip()
            banner.badge_text = request.POST.get('badge_text', '').strip()
            banner.button_text = request.POST.get('button_text', 'Shop Now').strip()
            banner.button_url = request.POST.get('button_url', '/products/').strip()
            banner.bg_gradient = request.POST.get('bg_gradient', 'from-neutral-950 via-slate-900 to-neutral-950').strip()
            banner.border_color = request.POST.get('border_color', 'border-slate-800/80').strip()
            banner.text_color_theme = request.POST.get('text_color_theme', 'dark').strip()
            banner.start_date = request.POST.get('start_date') or None
            banner.end_date = request.POST.get('end_date') or None
            banner.is_active = bool(request.POST.get('is_active'))
            banner.display_order = int(request.POST.get('display_order', 0) or 0)
            
            uploaded_image = request.FILES.get('image')
            if uploaded_image:
                banner.image = uploaded_image
            elif request.POST.get('clear_image') in ['on', 'true', 'True', '1']:
                banner.image = None

            banner.image_url = request.POST.get('image_url', '').strip()
            banner.save()
            messages.success(request, f"Banner '{banner.title}' updated successfully.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'cms:banners')


def cms_banner_toggle_view(request, banner_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    banner = get_object_or_404(PromoBanner, id=banner_id)
    banner.is_active = not banner.is_active
    banner.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f"Banner '{banner.title}' is now {'Active' if banner.is_active else 'Inactive'}.")
    return redirect('cms:banners')


def cms_banner_bulk_action_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No banners selected.")
            return redirect('cms:banners')

        qs = PromoBanner.objects.filter(id__in=selected_ids)
        count = qs.count()

        if action == 'activate':
            qs.update(is_active=True, updated_at=timezone.now())
            messages.success(request, f"Activated {count} selected banner(s).")
        elif action == 'deactivate':
            qs.update(is_active=False, updated_at=timezone.now())
            messages.success(request, f"Deactivated {count} selected banner(s).")
        elif action == 'delete':
            qs.delete()
            messages.success(request, f"Deleted {count} selected banner(s).")
        else:
            messages.error(request, "Invalid bulk action.")
    return redirect('cms:banners')


# ==============================================================================
# 2. HOMEPAGE SECTION BLOCKS
# ==============================================================================
def cms_sections_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'sections')
    qs = HomepageSection.objects.all().order_by('display_order', 'id')

    section_type = request.GET.get('section_type', 'all')
    if section_type != 'all':
        qs = qs.filter(section_type=section_type)

    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(title__icontains=q) | Q(subtitle__icontains=q))

    sections = list(qs)
    context.update({
        'sections': sections,
        'section_type_filter': section_type,
        'status_filter': status_filter,
        'search_query': q,
        'section_types': HomepageSection.SECTION_TYPES,
        'filter_types': HomepageSection.FILTER_TYPES,
        'total_count': len(sections),
    })
    return render(request, 'cms/sections.html', context)


def cms_section_add_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        section_type = request.POST.get('section_type', 'category_bar')
        if not name:
            messages.error(request, "Section Name is required.")
            return redirect('cms:sections')

        uploaded_image = request.FILES.get('image')
        section = HomepageSection.objects.create(
            name=name,
            section_type=section_type,
            title=request.POST.get('title', '').strip(),
            subtitle=request.POST.get('subtitle', '').strip(),
            image=uploaded_image if uploaded_image else None,
            image_url=request.POST.get('image_url', '').strip(),
            view_all_url=request.POST.get('view_all_url', '/products/').strip(),
            view_all_text=request.POST.get('view_all_text', 'Explore All').strip(),
            product_filter_type=request.POST.get('product_filter_type', 'trending'),
            max_items=int(request.POST.get('max_items', 4) or 4),
            is_active=bool(request.POST.get('is_active')),
            display_order=int(request.POST.get('display_order', 0) or 0),
        )
        messages.success(request, f"Section '{section.name}' created successfully.")
    return redirect('cms:sections')


def cms_section_edit_view(request, section_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    section = get_object_or_404(HomepageSection, id=section_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, "Section Name is required.")
        else:
            section.name = name
            section.section_type = request.POST.get('section_type', section.section_type)
            section.title = request.POST.get('title', '').strip()
            section.subtitle = request.POST.get('subtitle', '').strip()
            
            uploaded_image = request.FILES.get('image')
            if uploaded_image:
                section.image = uploaded_image
            elif request.POST.get('clear_image') in ['on', 'true', 'True', '1']:
                section.image = None

            section.image_url = request.POST.get('image_url', '').strip()
            section.view_all_url = request.POST.get('view_all_url', '/products/').strip()
            section.view_all_text = request.POST.get('view_all_text', 'Explore All').strip()
            section.product_filter_type = request.POST.get('product_filter_type', 'trending')
            section.max_items = int(request.POST.get('max_items', 4) or 4)
            section.is_active = bool(request.POST.get('is_active'))
            section.display_order = int(request.POST.get('display_order', 0) or 0)
            section.save()
            messages.success(request, f"Section '{section.name}' updated successfully.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'cms:sections')


def cms_section_toggle_view(request, section_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    section = get_object_or_404(HomepageSection, id=section_id)
    section.is_active = not section.is_active
    section.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f"Section '{section.name}' is now {'Active' if section.is_active else 'Inactive'}.")
    return redirect('cms:sections')


def cms_section_bulk_action_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No sections selected.")
            return redirect('cms:sections')

        qs = HomepageSection.objects.filter(id__in=selected_ids)
        count = qs.count()

        if action == 'activate':
            qs.update(is_active=True, updated_at=timezone.now())
            messages.success(request, f"Activated {count} selected section(s).")
        elif action == 'deactivate':
            qs.update(is_active=False, updated_at=timezone.now())
            messages.success(request, f"Deactivated {count} selected section(s).")
        elif action == 'delete':
            qs.delete()
            messages.success(request, f"Deleted {count} selected section(s).")
    return redirect('cms:sections')


# ==============================================================================
# 3. CATEGORY SUB-MENU NAVIGATION ITEMS
# ==============================================================================
def cms_category_nav_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'category_nav')
    qs = CategoryNavItem.objects.all().select_related('category').order_by('display_order', 'id')

    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    highlight_filter = request.GET.get('highlight', 'all')
    if highlight_filter == 'highlighted':
        qs = qs.filter(is_highlighted=True)
    elif highlight_filter == 'regular':
        qs = qs.filter(is_highlighted=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(category__name__icontains=q) | Q(custom_url__icontains=q))

    items = list(qs)
    context.update({
        'nav_items': items,
        'status_filter': status_filter,
        'highlight_filter': highlight_filter,
        'search_query': q,
        'catalog_categories': Category.objects.filter(is_active=True).order_by('name'),
        'total_count': len(items),
    })
    return render(request, 'cms/category_nav.html', context)


def cms_category_nav_add_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Item Title is required.")
            return redirect('cms:category_nav')

        cat_id = request.POST.get('category')
        category = Category.objects.filter(id=cat_id).first() if cat_id else None

        uploaded_image = request.FILES.get('image')
        item = CategoryNavItem.objects.create(
            title=title,
            category=category,
            custom_url=request.POST.get('custom_url', '').strip(),
            icon_name=request.POST.get('icon_name', 'sparkles').strip(),
            image=uploaded_image if uploaded_image else None,
            image_url=request.POST.get('image_url', '').strip(),
            is_highlighted=bool(request.POST.get('is_highlighted')),
            is_active=bool(request.POST.get('is_active')),
            display_order=int(request.POST.get('display_order', 0) or 0),
        )
        messages.success(request, f"Sub-menu item '{item.title}' created successfully.")
    return redirect('cms:category_nav')


def cms_category_nav_edit_view(request, item_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    item = get_object_or_404(CategoryNavItem, id=item_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Item Title is required.")
        else:
            item.title = title
            cat_id = request.POST.get('category')
            item.category = Category.objects.filter(id=cat_id).first() if cat_id else None
            item.custom_url = request.POST.get('custom_url', '').strip()
            item.icon_name = request.POST.get('icon_name', 'sparkles').strip()
            
            uploaded_image = request.FILES.get('image')
            if uploaded_image:
                item.image = uploaded_image
            elif request.POST.get('clear_image') in ['on', 'true', 'True', '1']:
                item.image = None

            item.image_url = request.POST.get('image_url', '').strip()
            item.is_highlighted = bool(request.POST.get('is_highlighted'))
            item.is_active = bool(request.POST.get('is_active'))
            item.display_order = int(request.POST.get('display_order', 0) or 0)
            item.save()
            messages.success(request, f"Sub-menu item '{item.title}' updated successfully.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'cms:category_nav')


def cms_category_nav_toggle_view(request, item_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    item = get_object_or_404(CategoryNavItem, id=item_id)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f"Item '{item.title}' is now {'Active' if item.is_active else 'Inactive'}.")
    return redirect('cms:category_nav')


def cms_category_nav_bulk_action_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No items selected.")
            return redirect('cms:category_nav')

        qs = CategoryNavItem.objects.filter(id__in=selected_ids)
        count = qs.count()

        if action == 'activate':
            qs.update(is_active=True, updated_at=timezone.now())
            messages.success(request, f"Activated {count} selected item(s).")
        elif action == 'deactivate':
            qs.update(is_active=False, updated_at=timezone.now())
            messages.success(request, f"Deactivated {count} selected item(s).")
        elif action == 'delete':
            qs.delete()
            messages.success(request, f"Deleted {count} selected item(s).")
    return redirect('cms:category_nav')


# ==============================================================================
# 4. CURATED CATEGORY SHOWCASES
# ==============================================================================
def cms_curations_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'curations')
    qs = HomepageCategoryItem.objects.all().select_related('category').order_by('display_order', 'id')

    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(custom_title__icontains=q) | Q(category__name__icontains=q) | Q(custom_subtitle__icontains=q))

    curations = list(qs)
    context.update({
        'curations': curations,
        'status_filter': status_filter,
        'search_query': q,
        'catalog_categories': Category.objects.filter(is_active=True).order_by('name'),
        'total_count': len(curations),
    })
    return render(request, 'cms/curations.html', context)


def cms_curation_add_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        cat_id = request.POST.get('category')
        category = Category.objects.filter(id=cat_id).first()
        if not category:
            messages.error(request, "Catalog Category is required.")
            return redirect('cms:curations')

        uploaded_image = request.FILES.get('custom_image')
        curation = HomepageCategoryItem.objects.create(
            category=category,
            custom_title=request.POST.get('custom_title', '').strip(),
            custom_subtitle=request.POST.get('custom_subtitle', '').strip(),
            custom_image=uploaded_image if uploaded_image else None,
            custom_image_url=request.POST.get('custom_image_url', '').strip(),
            badge_text=request.POST.get('badge_text', '').strip(),
            badge_color=request.POST.get('badge_color', 'blue').strip(),
            link_url=request.POST.get('link_url', '').strip(),
            is_active=bool(request.POST.get('is_active')),
            display_order=int(request.POST.get('display_order', 0) or 0),
        )
        messages.success(request, f"Curated showcase for '{curation.display_title}' created successfully.")
    return redirect('cms:curations')


def cms_curation_edit_view(request, item_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    curation = get_object_or_404(HomepageCategoryItem, id=item_id)
    if request.method == 'POST':
        cat_id = request.POST.get('category')
        category = Category.objects.filter(id=cat_id).first() if cat_id else curation.category
        if not category:
            messages.error(request, "Catalog Category is required.")
        else:
            curation.category = category
            curation.custom_title = request.POST.get('custom_title', '').strip()
            curation.custom_subtitle = request.POST.get('custom_subtitle', '').strip()
            
            uploaded_image = request.FILES.get('custom_image')
            if uploaded_image:
                curation.custom_image = uploaded_image
            elif request.POST.get('clear_image') in ['on', 'true', 'True', '1']:
                curation.custom_image = None

            curation.custom_image_url = request.POST.get('custom_image_url', '').strip()
            curation.badge_text = request.POST.get('badge_text', '').strip()
            curation.badge_color = request.POST.get('badge_color', 'blue').strip()
            curation.link_url = request.POST.get('link_url', '').strip()
            curation.is_active = bool(request.POST.get('is_active'))
            curation.display_order = int(request.POST.get('display_order', 0) or 0)
            curation.save()
            messages.success(request, f"Curated showcase for '{curation.display_title}' updated successfully.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'cms:curations')


def cms_curation_toggle_view(request, item_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    item = get_object_or_404(HomepageCategoryItem, id=item_id)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f"Showcase '{item.display_title}' is now {'Active' if item.is_active else 'Inactive'}.")
    return redirect('cms:curations')


def cms_curation_bulk_action_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No showcases selected.")
            return redirect('cms:curations')

        qs = HomepageCategoryItem.objects.filter(id__in=selected_ids)
        count = qs.count()

        if action == 'activate':
            qs.update(is_active=True, updated_at=timezone.now())
            messages.success(request, f"Activated {count} selected showcase(s).")
        elif action == 'deactivate':
            qs.update(is_active=False, updated_at=timezone.now())
            messages.success(request, f"Deactivated {count} selected showcase(s).")
        elif action == 'delete':
            qs.delete()
            messages.success(request, f"Deleted {count} selected showcase(s).")
    return redirect('cms:curations')


# ==============================================================================
# 5. VALUE PROPOSITIONS & TRUST BADGES
# ==============================================================================
def cms_trust_badges_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'trust_badges')
    qs = TrustBadge.objects.all().order_by('display_order', 'id')

    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(subtitle__icontains=q))

    badges = list(qs)
    context.update({
        'trust_badges': badges,
        'status_filter': status_filter,
        'search_query': q,
        'total_count': len(badges),
    })
    return render(request, 'cms/trust_badges.html', context)


def cms_trust_badge_add_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        subtitle = request.POST.get('subtitle', '').strip()
        if not title:
            messages.error(request, "Badge Title is required.")
            return redirect('cms:trust_badges')

        badge = TrustBadge.objects.create(
            title=title,
            subtitle=subtitle,
            icon_name=request.POST.get('icon_name', 'truck').strip(),
            color_theme=request.POST.get('color_theme', 'blue').strip(),
            is_active=bool(request.POST.get('is_active')),
            display_order=int(request.POST.get('display_order', 0) or 0),
        )
        messages.success(request, f"Trust badge '{badge.title}' created successfully.")
    return redirect('cms:trust_badges')


def cms_trust_badge_edit_view(request, badge_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    badge = get_object_or_404(TrustBadge, id=badge_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Badge Title is required.")
        else:
            badge.title = title
            badge.subtitle = request.POST.get('subtitle', '').strip()
            badge.icon_name = request.POST.get('icon_name', 'truck').strip()
            badge.color_theme = request.POST.get('color_theme', 'blue').strip()
            badge.is_active = bool(request.POST.get('is_active'))
            badge.display_order = int(request.POST.get('display_order', 0) or 0)
            badge.save()
            messages.success(request, f"Trust badge '{badge.title}' updated successfully.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'cms:trust_badges')


def cms_trust_badge_toggle_view(request, badge_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    badge = get_object_or_404(TrustBadge, id=badge_id)
    badge.is_active = not badge.is_active
    badge.save(update_fields=['is_active'])
    messages.success(request, f"Badge '{badge.title}' is now {'Active' if badge.is_active else 'Inactive'}.")
    return redirect('cms:trust_badges')


def cms_trust_badge_bulk_action_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No badges selected.")
            return redirect('cms:trust_badges')

        qs = TrustBadge.objects.filter(id__in=selected_ids)
        count = qs.count()

        if action == 'activate':
            qs.update(is_active=True)
            messages.success(request, f"Activated {count} selected badge(s).")
        elif action == 'deactivate':
            qs.update(is_active=False)
            messages.success(request, f"Deactivated {count} selected badge(s).")
        elif action == 'delete':
            qs.delete()
            messages.success(request, f"Deleted {count} selected badge(s).")
    return redirect('cms:trust_badges')


# ==============================================================================
# 6. GLOBAL NAVIGATION BAR HIERARCHY
# ==============================================================================
def cms_navbar_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    context = _get_cms_context_base(request, 'navbar')
    qs = NavbarItem.objects.all().select_related('parent').prefetch_related('children').order_by('display_order', 'id')

    status_filter = request.GET.get('status', 'all')
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    parent_filter = request.GET.get('type', 'all')
    if parent_filter == 'root':
        qs = qs.filter(parent__isnull=True)
    elif parent_filter == 'dropdown':
        qs = qs.filter(parent__isnull=False)

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(url__icontains=q) | Q(badge_text__icontains=q))

    items = list(qs)
    context.update({
        'navbar_items': items,
        'status_filter': status_filter,
        'parent_filter': parent_filter,
        'search_query': q,
        'root_items': NavbarItem.objects.filter(parent__isnull=True).order_by('display_order', 'title'),
        'total_count': len(items),
    })
    return render(request, 'cms/navbar.html', context)


def cms_navbar_add_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        url = request.POST.get('url', '#').strip()
        if not title:
            messages.error(request, "Menu Item Title is required.")
            return redirect('cms:navbar')

        parent_id = request.POST.get('parent')
        parent = NavbarItem.objects.filter(id=parent_id).first() if parent_id else None

        item = NavbarItem.objects.create(
            title=title,
            url=url,
            parent=parent,
            badge_text=request.POST.get('badge_text', '').strip(),
            badge_color=request.POST.get('badge_color', 'amber').strip(),
            open_in_new_tab=bool(request.POST.get('open_in_new_tab')),
            is_active=bool(request.POST.get('is_active')),
            display_order=int(request.POST.get('display_order', 0) or 0),
        )
        messages.success(request, f"Navbar item '{item.title}' created successfully.")
    return redirect('cms:navbar')


def cms_navbar_edit_view(request, item_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    item = get_object_or_404(NavbarItem, id=item_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        url = request.POST.get('url', '#').strip()
        if not title:
            messages.error(request, "Menu Item Title is required.")
        else:
            item.title = title
            item.url = url
            parent_id = request.POST.get('parent')
            if parent_id and str(parent_id) != str(item.id):
                item.parent = NavbarItem.objects.filter(id=parent_id).first()
            else:
                item.parent = None
            item.badge_text = request.POST.get('badge_text', '').strip()
            item.badge_color = request.POST.get('badge_color', 'amber').strip()
            item.open_in_new_tab = bool(request.POST.get('open_in_new_tab'))
            item.is_active = bool(request.POST.get('is_active'))
            item.display_order = int(request.POST.get('display_order', 0) or 0)
            item.save()
            messages.success(request, f"Navbar item '{item.title}' updated successfully.")

    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
    return redirect(next_url or 'cms:navbar')


def cms_navbar_toggle_view(request, item_id: int):
    if not _check_cms_access(request):
        return redirect('management:portal')

    item = get_object_or_404(NavbarItem, id=item_id)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f"Menu item '{item.title}' is now {'Active' if item.is_active else 'Inactive'}.")
    return redirect('cms:navbar')


def cms_navbar_bulk_action_view(request):
    if not _check_cms_access(request):
        return redirect('management:portal')

    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No menu items selected.")
            return redirect('cms:navbar')

        qs = NavbarItem.objects.filter(id__in=selected_ids)
        count = qs.count()

        if action == 'activate':
            qs.update(is_active=True, updated_at=timezone.now())
            messages.success(request, f"Activated {count} selected item(s).")
        elif action == 'deactivate':
            qs.update(is_active=False, updated_at=timezone.now())
            messages.success(request, f"Deactivated {count} selected item(s).")
        elif action == 'delete':
            qs.delete()
            messages.success(request, f"Deleted {count} selected item(s).")
    return redirect('cms:navbar')


