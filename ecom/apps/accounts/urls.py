from django.urls import path

try:
    from . import views
except (ImportError, ValueError):
    try:
        from apps.accounts import views
    except (ImportError, ValueError):
        import views  # type: ignore

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
]
