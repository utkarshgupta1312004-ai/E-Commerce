from django.urls import path
from . import management_views

app_name = 'management'

urlpatterns = [
    path('', management_views.management_page_view, name='portal'),
    path('dashboard/', management_views.superadmin_dashboard_view, name='dashboard'),
    path('sales/', management_views.superadmin_sales_view, name='sales'),
    path('analytics/', management_views.superadmin_analytics_view, name='analytics'),
    path('domains/', management_views.superadmin_domains_view, name='domains'),
    path('users/', management_views.superadmin_users_view, name='users'),
    path('departments/accounts/', management_views.superadmin_department_accounts_view, name='department_accounts'),
    path('departments/<int:dept_id>/configure/', management_views.superadmin_configure_department_account, name='configure_dept_account'),
    path('departments/<int:dept_id>/edit-login-id/', management_views.superadmin_edit_department_login_id, name='edit_dept_login_id'),
    path('departments/<int:dept_id>/reset-password/', management_views.superadmin_reset_department_password, name='reset_dept_password'),
    path('departments/<int:dept_id>/status/<str:new_status>/', management_views.superadmin_change_department_status, name='change_dept_status'),
    path('departments/<int:dept_id>/generate-credentials/', management_views.api_generate_department_credentials, name='generate_dept_credentials'),
    path('department/login/', management_views.department_login_view, name='dept_login'),
    path('department/logout/', management_views.department_logout_view, name='dept_logout'),
    path('login/', management_views.superadmin_login_view, name='login'),
    path('logout/', management_views.superadmin_logout_view, name='logout'),
]

