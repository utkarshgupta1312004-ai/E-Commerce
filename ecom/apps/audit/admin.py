from typing import Any
from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display: Any = ('timestamp', 'action', 'get_actor', 'department', 'ip_address', 'path')
    list_filter: Any = ('action', 'department', 'timestamp')
    search_fields: Any = ('user__username', 'username_attempt', 'ip_address', 'details', 'path')
    readonly_fields: Any = ('timestamp', 'action', 'user', 'username_attempt', 'department', 'ip_address', 'user_agent', 'path', 'details')
    ordering: Any = ('-timestamp',)

    @admin.display(description='User / Actor')
    def get_actor(self, obj) -> str:
        return obj.user.username if obj.user else (obj.username_attempt or 'Anonymous')

    def has_add_permission(self, request) -> bool:
        return False  # Audit logs cannot be manually added via admin

    def has_change_permission(self, request, obj=None) -> bool:
        return False  # Audit logs are immutable

    def has_delete_permission(self, request, obj=None) -> bool:
        return request.user.is_superuser  # Only superuser may purge logs
