from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('dashboard/', views.inventory_dashboard_view, name='dashboard'),
    path('stock/', views.stock_list_view, name='stock_list'),
    path('warehouses/', views.warehouse_list_view, name='warehouse_list'),
    path('warehouses/<int:pk>/', views.warehouse_detail_view, name='warehouse_detail'),
    path('movements/', views.stock_movement_list_view, name='movement_list'),
    path('adjustments/', views.stock_adjustment_view, name='stock_adjustments'),
    path('transfers/', views.stock_transfer_view, name='stock_transfers'),
]
