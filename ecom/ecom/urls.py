"""
URL configuration for ecom project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

# Direct admin login redirect to Superadmin Dashboard (admindash)
_original_admin_login = admin.site.login

def _admindash_redirecting_admin_login(request, extra_context=None):
    if request.user.is_authenticated and request.user.is_superuser and request.method == 'GET':
        return redirect('management:dashboard')
    response = _original_admin_login(request, extra_context)
    if request.method == 'POST' and request.user.is_authenticated and request.user.is_superuser:
        request.session.cycle_key()
        return redirect('management:dashboard')
    return response

admin.site.login = _admindash_redirecting_admin_login

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('management/', include('apps.core.management_urls', namespace='management')),
    path('inventory/', include('apps.inventory.urls', namespace='inventory')),
    path('cart/', include('apps.cart.urls', namespace='cart')),
    path('wishlist/', include('apps.wishlist.urls', namespace='wishlist')),
    path('checkout/', include('apps.checkout.urls', namespace='checkout')),
    path('orders/', include('apps.orders.urls', namespace='orders')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('reviews/', include('apps.reviews.urls', namespace='reviews')),
    path('api/assistant/', include('apps.assistant.urls', namespace='assistant')),
    path('', include('apps.catalog.urls', namespace='catalog')),
    path('', include('apps.cms.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

