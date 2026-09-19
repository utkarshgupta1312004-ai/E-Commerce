from .models import AuditLog


class AuditService:
    @staticmethod
    def get_client_ip(request):
        """Extract client IP from request headers or remote addr."""
        if not request:
            return None
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @classmethod
    def log(cls, action, request=None, user=None, username_attempt="", department="", details=""):
        """
        Record an immutable audit log entry.
        """
        try:
            ip = cls.get_client_ip(request) if request else None
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:250] if request else ""
            path = request.path[:250] if request else ""

            # If user not passed, attempt from request
            if user is None and request and hasattr(request, 'user') and request.user.is_authenticated:
                user = request.user

            return AuditLog.objects.create(
                user=user if (user and user.is_authenticated) else None,
                username_attempt=username_attempt or (user.username if user and hasattr(user, 'username') else ""),
                action=action,
                department=department,
                ip_address=ip,
                user_agent=user_agent,
                path=path,
                details=details
            )
        except Exception as e:
            # Audit logging failure should not crash the core application flow
            import logging
            logging.getLogger(__name__).error(f"Failed to record audit log: {e}")
            return None
