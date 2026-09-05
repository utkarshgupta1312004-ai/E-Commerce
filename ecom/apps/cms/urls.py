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
]
