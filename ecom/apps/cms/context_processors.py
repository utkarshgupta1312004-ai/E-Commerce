from django.db.models import Prefetch
from .models import NavbarItem, CategoryNavItem


def cms_context(request):
    """
    Context processor making CMS-managed navigation available across all storefront templates.
    """
    active_children_prefetch = Prefetch(
        'children',
        queryset=NavbarItem.objects.filter(is_active=True).order_by('display_order', 'id'),
        to_attr='prefetched_active_children'
    )

    navbar_items = NavbarItem.objects.filter(
        parent__isnull=True,
        is_active=True
    ).prefetch_related(active_children_prefetch).order_by('display_order', 'id')

    category_nav_items = CategoryNavItem.objects.filter(
        is_active=True
    ).select_related('category').order_by('display_order', 'id')

    return {
        'cms_navbar_items': navbar_items,
        'cms_category_nav_items': category_nav_items,
    }
