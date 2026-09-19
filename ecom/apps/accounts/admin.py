from typing import Any
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from .models import Role, UserProfile, Address

User = get_user_model()


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'address_type', 'city', 'state', 'postal_code', 'is_default', 'created_at')
    list_filter = ('address_type', 'is_default', 'state', 'country')
    search_fields = ('user__username', 'full_name', 'street_address', 'city', 'phone')


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Staff Management Profile & Department Access'
    filter_horizontal = ('roles', 'department_access')
    fieldsets = (
        ('Staff Status', {
            'fields': ('is_management_staff', 'job_title', 'phone')
        }),
        ('Department Access & Roles', {
            'fields': ('roles', 'department_access'),
            'description': 'Assign management roles or direct department access to this staff member.'
        }),
    )


# Unregister default User admin and re-register with UserProfileInline
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    inlines: Any = (UserProfileInline,)
    list_display: Any = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'get_roles', 'is_active')
    list_filter: Any = ('is_staff', 'is_superuser', 'is_active', 'profile__is_management_staff')

    @admin.display(description='Management Roles')
    def get_roles(self, obj) -> str:
        if hasattr(obj, 'profile'):
            roles = [r.name for r in obj.profile.roles.all()]
            return ", ".join(roles) if roles else ("Super Admin" if obj.is_superuser else "-")
        return "-"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display: Any = ('name', 'code', 'is_superadmin', 'get_departments_count', 'created_at')
    list_filter: Any = ('is_superadmin',)
    search_fields = ('name', 'code', 'description')
    filter_horizontal = ('departments', 'permissions')
    prepopulated_fields = {'code': ('name',)}
    fieldsets = (
        ('Role Information', {
            'fields': ('name', 'code', 'description', 'is_superadmin')
        }),
        ('Department Permissions', {
            'fields': ('departments',),
            'description': 'Select all management departments this role is authorized to access.'
        }),
        ('Granular Django Permissions', {
            'fields': ('permissions',),
            'description': 'Select specific model-level permissions associated with this role.'
        }),
    )

    @admin.display(description='Assigned Departments')
    def get_departments_count(self, obj) -> int:
        return obj.departments.count()


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display: Any = ('user', 'job_title', 'is_management_staff', 'get_roles_display', 'get_departments_display')
    list_filter: Any = ('is_management_staff', 'roles')
    search_fields = ('user__username', 'user__email', 'job_title')
    filter_horizontal = ('roles', 'department_access')

    @admin.display(description='Roles')
    def get_roles_display(self, obj) -> str:
        return ", ".join([r.name for r in obj.roles.all()]) or ("Super Admin" if obj.user.is_superuser else "None")

    @admin.display(description='Accessible Departments')
    def get_departments_display(self, obj) -> str:
        return ", ".join([d.name for d in obj.get_accessible_departments()])
