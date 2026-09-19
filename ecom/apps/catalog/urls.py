from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Customer Storefront Routes
    path('products/', views.product_list_view, name='product_list'),
    path('products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('products/<slug:slug>/buy/', views.product_buy_now_view, name='product_buy'),
    path('category/<slug:slug>/', views.category_detail_view, name='category_detail'),

    # Catalog Management Console Routes
    path('catalog/dashboard/', views.catalog_dashboard_view, name='dashboard'),
    path('catalog/products/', views.product_admin_list_view, name='product_admin_list'),
    path('catalog/products/add/', views.product_add_view, name='product_add'),
    path('catalog/products/<int:pk>/edit/', views.product_edit_view, name='product_edit'),
    path('catalog/products/<int:pk>/archive/', views.product_archive_view, name='product_archive'),
    path('catalog/products/<int:pk>/toggle-status/', views.product_toggle_status_view, name='product_toggle_status'),

    # Category Management
    path('catalog/categories/', views.category_list_view, name='category_list'),
    path('catalog/categories/add/', views.category_add_view, name='category_add'),
    path('catalog/categories/<int:pk>/edit/', views.category_edit_view, name='category_edit'),
    path('catalog/categories/<int:pk>/toggle-status/', views.category_toggle_status_view, name='category_toggle_status'),

    # Brand Management
    path('catalog/brands/', views.brand_list_view, name='brand_list'),
    path('catalog/brands/add/', views.brand_add_view, name='brand_add'),
    path('catalog/brands/<int:pk>/edit/', views.brand_edit_view, name='brand_edit'),
    path('catalog/brands/<int:pk>/toggle-status/', views.brand_toggle_status_view, name='brand_toggle_status'),

    # Attribute Management
    path('catalog/attributes/', views.attribute_list_view, name='attribute_list'),
    path('catalog/attributes/add/', views.attribute_add_view, name='attribute_add'),
    path('catalog/attributes/<int:pk>/edit/', views.attribute_edit_view, name='attribute_edit'),
    path('catalog/attributes/<int:pk>/delete/', views.attribute_delete_view, name='attribute_delete'),
]
