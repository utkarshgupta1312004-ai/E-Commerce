from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('google/login/', views.google_login_view, name='google_login'),
    path('google/callback/', views.google_callback_view, name='google_callback'),
    path('google/callback', views.google_callback_view),
    path('profile/', views.profile_view, name='profile'),
    path('password/change/', views.change_password_view, name='change_password'),
    path('settings/', views.account_settings_view, name='settings'),

    # Accounts Department Management Console
    path('manage/', views.accounts_dashboard_view, name='dashboard'),
    path('manage/users/<int:user_id>/', views.accounts_user_detail_view, name='user_detail'),
    path('manage/users/add/', views.accounts_user_add_view, name='user_add'),
    path('manage/users/<int:user_id>/toggle-status/', views.accounts_user_toggle_status_view, name='user_toggle_status'),
    path('manage/users/<int:user_id>/address/add/', views.accounts_address_add_view, name='user_address_add'),
    path('manage/users/<int:user_id>/address/<int:address_id>/delete/', views.accounts_address_delete_view, name='user_address_delete'),
    path('manage/roles/', views.accounts_roles_view, name='roles'),
]

