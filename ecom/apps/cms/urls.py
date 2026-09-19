from django.urls import path

try:
    from . import views
except (ImportError, ValueError):
    try:
        from apps.cms import views
    except (ImportError, ValueError):
        import views  # type: ignore

app_name = 'cms'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('cms/dashboard/', views.cms_dashboard_view, name='dashboard'),

    # 1. Hero & Promotional Banners
    path('cms/banners/', views.cms_banners_view, name='banners'),
    path('cms/banners/add/', views.cms_banner_add_view, name='banner_add'),
    path('cms/banners/edit/<int:banner_id>/', views.cms_banner_edit_view, name='banner_edit'),
    path('cms/banners/toggle/<int:banner_id>/', views.cms_banner_toggle_view, name='banner_toggle'),
    path('cms/banners/bulk/', views.cms_banner_bulk_action_view, name='banner_bulk'),

    # 2. Homepage Section Blocks
    path('cms/sections/', views.cms_sections_view, name='sections'),
    path('cms/sections/add/', views.cms_section_add_view, name='section_add'),
    path('cms/sections/edit/<int:section_id>/', views.cms_section_edit_view, name='section_edit'),
    path('cms/sections/toggle/<int:section_id>/', views.cms_section_toggle_view, name='section_toggle'),
    path('cms/sections/bulk/', views.cms_section_bulk_action_view, name='section_bulk'),

    # 3. Category Sub-Menu Navigation Items
    path('cms/category-nav/', views.cms_category_nav_view, name='category_nav'),
    path('cms/category-nav/add/', views.cms_category_nav_add_view, name='category_nav_add'),
    path('cms/category-nav/edit/<int:item_id>/', views.cms_category_nav_edit_view, name='category_nav_edit'),
    path('cms/category-nav/toggle/<int:item_id>/', views.cms_category_nav_toggle_view, name='category_nav_toggle'),
    path('cms/category-nav/bulk/', views.cms_category_nav_bulk_action_view, name='category_nav_bulk'),

    # 4. Curated Category Showcases
    path('cms/curations/', views.cms_curations_view, name='curations'),
    path('cms/curations/add/', views.cms_curation_add_view, name='curation_add'),
    path('cms/curations/edit/<int:item_id>/', views.cms_curation_edit_view, name='curation_edit'),
    path('cms/curations/toggle/<int:item_id>/', views.cms_curation_toggle_view, name='curation_toggle'),
    path('cms/curations/bulk/', views.cms_curation_bulk_action_view, name='curation_bulk'),

    # 5. Value Propositions & Trust Badges
    path('cms/trust-badges/', views.cms_trust_badges_view, name='trust_badges'),
    path('cms/trust-badges/add/', views.cms_trust_badge_add_view, name='trust_badge_add'),
    path('cms/trust-badges/edit/<int:badge_id>/', views.cms_trust_badge_edit_view, name='trust_badge_edit'),
    path('cms/trust-badges/toggle/<int:badge_id>/', views.cms_trust_badge_toggle_view, name='trust_badge_toggle'),
    path('cms/trust-badges/bulk/', views.cms_trust_badge_bulk_action_view, name='trust_badge_bulk'),

    # 6. Global Navigation Bar Hierarchy
    path('cms/navbar/', views.cms_navbar_view, name='navbar'),
    path('cms/navbar/add/', views.cms_navbar_add_view, name='navbar_add'),
    path('cms/navbar/edit/<int:item_id>/', views.cms_navbar_edit_view, name='navbar_edit'),
    path('cms/navbar/toggle/<int:item_id>/', views.cms_navbar_toggle_view, name='navbar_toggle'),
    path('cms/navbar/bulk/', views.cms_navbar_bulk_action_view, name='navbar_bulk'),
]
