from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail_view, name='cart_detail'),
    path('add/', views.add_to_cart_view, name='add_to_cart'),
    path('update/', views.update_cart_view, name='update_cart'),
    path('remove/', views.remove_from_cart_view, name='remove_from_cart'),
    path('clear/', views.clear_cart_view, name='clear_cart'),
]
