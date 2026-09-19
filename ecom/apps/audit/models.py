from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Central immutable log recording authentication events, department access,
    permission denials, and staff administrative activities.
    """
    ACTION_CHOICES = (
        ('login_success', 'Management Login Success'),
        ('login_failure', 'Management Login Failure'),
        ('logout', 'Management Logout'),
        ('dept_access', 'Department Access'),
        ('permission_denied', 'Permission Denied'),
        ('create', 'Resource Created'),
        ('update', 'Resource Updated'),
        ('delete', 'Resource Deleted'),
        ('admin_action', 'Administrative Action'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User involved in this event (null if unauthenticated or failed login)"
    )
    username_attempt = models.CharField(max_length=150, blank=True, default="", help_text="Username attempted on login")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, db_index=True)
    department = models.CharField(max_length=100, blank=True, default="", db_index=True, help_text="Target department slug or name")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    path = models.CharField(max_length=255, blank=True, default="")
    details = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Audit & Security Log'
        verbose_name_plural = 'Audit & Security Logs'
        ordering = ['-timestamp']

    @property
    def clean_action(self):
        if self.action.startswith('assistant_tool_'):
            tool = self.action.replace('assistant_tool_', '').replace('_', ' ').strip().title()
            return f"AI: {tool}"
        disp = self.get_action_display()
        return disp.replace('Management ', '')

    def __str__(self):
        user_str = self.user.username if self.user else (self.username_attempt or 'Anonymous')
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.get_action_display()} - {user_str} ({self.department or 'System'})"
