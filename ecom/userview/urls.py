from django.urls import path,include
from userview import views

app_name = 'userview'

urlpatterns = [
    # Storefront & Discovery
    path('', views.home_view, name='home'),
    
   
]
