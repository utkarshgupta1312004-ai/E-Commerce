from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist_view, name='wishlist_view'),
    path('toggle/', views.toggle_wishlist_view, name='toggle_wishlist'),
    path('remove/<int:item_id>/', views.remove_wishlist_item_view, name='remove_item'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart_from_wishlist_view, name='add_to_cart'),
    path('move-to-cart/<int:item_id>/', views.move_to_cart_view, name='move_to_cart'),
    path('add-all-to-cart/', views.add_all_to_cart_view, name='add_all_to_cart'),
    path('clear/', views.clear_wishlist_view, name='clear_wishlist'),
]
