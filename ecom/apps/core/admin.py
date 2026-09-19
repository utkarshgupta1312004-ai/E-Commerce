from django.contrib import admin
from .models import ManagementDepartment, DepartmentAccount


class DepartmentAccountInline(admin.StackedInline):
    model = DepartmentAccount
    can_delete = False
    verbose_name = 'Department Login Account'
    verbose_name_plural = 'Department Login Account'
    fields = ('login_id', 'status', 'last_login')
    readonly_fields = ('last_login',)
    extra = 0


@admin.register(ManagementDepartment)
class ManagementDepartmentAdmin(admin.ModelAdmin):
    list_display = ('display_order', 'name', 'slug', 'code', 'icon', 'accent_color', 'is_active', 'login_required')
    list_display_links = ('name',)
    list_editable = ('display_order', 'is_active', 'accent_color')
    list_filter = ('is_active', 'login_required', 'accent_color')
    search_fields = ('name', 'slug', 'code', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order', 'name')
    inlines = [DepartmentAccountInline]
    fieldsets = (
        ('Department Identity', {
            'fields': ('name', 'slug', 'code', 'description', 'icon', 'accent_color')
        }),
        ('Access & Security', {
            'fields': ('required_permission', 'login_required', 'is_active')
        }),
        ('Portal Display Order', {
            'fields': ('display_order', 'url_name')
        }),
    )


@admin.register(DepartmentAccount)
class DepartmentAccountAdmin(admin.ModelAdmin):
    list_display = ('department', 'login_id', 'status', 'last_login', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('login_id', 'department__name', 'department__code')
    readonly_fields = ('password_hash', 'last_login', 'created_at', 'updated_at')

