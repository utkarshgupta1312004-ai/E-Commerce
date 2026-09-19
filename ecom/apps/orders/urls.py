from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Customer Storefront Order Views
    path('', views.order_list_view, name='order_list'),
    path('success/<str:order_number>/', views.order_success_view, name='order_success'),
    path('<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('<str:order_number>/receipt/', views.order_receipt_view, name='order_receipt'),

    # Enterprise Order Management Console (matching inventory management)
    path('manage/dashboard/', views.orders_management_dashboard_view, name='manage_dashboard'),
    path('manage/all/', views.orders_management_list_view, name='manage_list'),
    path('manage/<str:order_number>/', views.orders_management_detail_view, name='manage_detail'),
    path('manage/<str:order_number>/status-update/', views.orders_management_status_update_view, name='manage_status_update'),
]
