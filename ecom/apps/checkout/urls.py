from django.urls import path
from . import views

app_name = 'checkout'

urlpatterns = [
    # Customer Storefront Checkout
    path('', views.checkout_view, name='checkout'),
    path('place-order/', views.place_order_view, name='place_order'),

    # Enterprise Checkout & Dispatch Management (CHK001)
    path('dashboard/', views.checkout_dashboard_view, name='dashboard'),
    path('manage/', views.checkout_dashboard_view, name='manage'),
    path('deliveries/', views.checkout_deliveries_view, name='deliveries'),
    path('delivery/<str:order_number>/', views.checkout_delivery_detail_view, name='delivery_detail'),
    path('delivery/<str:order_number>/update/', views.checkout_delivery_update_view, name='delivery_update'),
]
