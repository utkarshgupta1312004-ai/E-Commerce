import logging
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.urls import reverse
from apps.core.models import DepartmentAccount

logger = logging.getLogger(__name__)


class UniversalSessionSecurityMiddleware:
    """
    Universal Session Security, Cache Prevention, and Crash-to-Login Middleware.
    Ensures that:
    1. Browser never caches authenticated pages or session cookies (Cache-Control: no-cache, no-store).
    2. Any session cookie sent by the browser is verified against backend storage (database).
    3. Stale, invalid, suspended, or missing backend sessions immediately flush and redirect to login.
    4. Any unhandled exception or crash on protected routes flushes the session and redirects to login.
    """

    PUBLIC_PATHS = (
        '/management/login/',
        '/management/department/login/',
        '/accounts/login/',
        '/accounts/register/',
        '/admin/login/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Pre-view session validation
        redirect_response = self.validate_session_storage(request)
        if redirect_response:
            return redirect_response

        # 2. Execute view with crash protection
        try:
            response = self.get_response(request)
        except Exception as exc:
            recovery_response = self.process_exception(request, exc)
            if recovery_response:
                return self.enforce_no_cache_headers(request, recovery_response)
            raise

        # 3. Post-view browser cache security headers
        return self.enforce_no_cache_headers(request, response)

    def validate_session_storage(self, request):
        """
        Verify that session credentials sent by browser cache/cookie correspond to
        active, valid records in the database.
        """
        path = request.path

        # Ignore static and media assets
        if path.startswith('/static/') or path.startswith('/media/'):
            return None

        user = getattr(request, 'user', None)
        is_superuser = bool(user and user.is_authenticated and user.is_superuser)
        is_authenticated_user = bool(user and user.is_authenticated)

        # Check CMS Studio Routes (/cms/...)
        if path.startswith('/cms/'):
            # Allow superuser
            if is_superuser:
                return None

            # Verify department account in database
            account_id = request.session.get('department_account_id')
            dept_slug = request.session.get('department_slug')

            if not account_id or dept_slug != 'cms':
                self._safe_flush_session(request)
                messages.error(request, "Your session has expired or is invalid. Please sign in with CMS credentials.")
                return redirect('management:portal')

            try:
                account = DepartmentAccount.objects.filter(
                    id=account_id,
                    department__slug='cms',
                    status=DepartmentAccount.STATUS_ACTIVE
                ).select_related('department').first()

                if not account:
                    self._safe_flush_session(request)
                    messages.error(request, "Your department account is no longer active or could not be found. Please sign in again.")
                    return redirect('management:portal')

            except Exception as e:
                logger.error(f"Database error during CMS session verification: {e}")
                self._safe_flush_session(request)
                messages.error(request, "A session verification error occurred. Please sign in again.")
                return redirect('management:portal')

        # Check Protected Superadmin Routes (/management/dashboard/, /management/sales/, etc.)
        elif path.startswith('/management/') and path not in ('/management/', '/management/login/', '/management/department/login/', '/management/department/logout/'):
            if not is_superuser:
                self._safe_flush_session(request)
                messages.error(request, "Access restricted. Please authenticate as Super Administrator.")
                return redirect('management:login')

            if user and not user.is_active:
                self._safe_flush_session(request)
                messages.error(request, "Your administrator account has been disabled. Please contact system support.")
                return redirect('management:login')

        # Check Department Session in Portal (/management/)
        elif path == '/management/':
            if is_superuser:
                return redirect('management:dashboard')
            dept_slug = request.session.get('department_slug')
            if dept_slug == 'cms':
                return redirect('cms:dashboard')

            account_id = request.session.get('department_account_id')
            if account_id:
                try:
                    account = DepartmentAccount.objects.filter(
                        id=account_id,
                        status=DepartmentAccount.STATUS_ACTIVE
                    ).first()
                    if not account:
                        self._clear_dept_session_keys(request)
                except Exception:
                    self._clear_dept_session_keys(request)

        # Check Customer Accounts Protected Routes (/accounts/dashboard/, /accounts/profile/, etc.)
        elif path.startswith('/accounts/') and path not in ('/accounts/login/', '/accounts/register/', '/accounts/'):
            if is_authenticated_user and user and not user.is_active:
                self._safe_flush_session(request)
                messages.error(request, "Your account is not active. Please sign in again.")
                return redirect('accounts:login')

        return None

    def enforce_no_cache_headers(self, request, response):
        """
        Enforce strict no-cache headers on all management, cms, accounts, and admin pages,
        or any response involving an authenticated session.
        Prevents browser disk/memory cache and Back/Forward cache (bfcache) from saving sensitive views.
        """
        path = request.path

        is_sensitive_path = (
            path.startswith('/management/') or
            path.startswith('/cms/') or
            path.startswith('/accounts/') or
            path.startswith('/admin/')
        )

        has_auth = (
            bool(getattr(request, 'user', None) and request.user.is_authenticated) or
            bool(request.session.get('department_account_id'))
        )

        if is_sensitive_path or has_auth:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response

    def process_exception(self, request, exception):
        """
        Universal Crash-to-Login Interceptor.
        If an unhandled exception or crash occurs anywhere on management, CMS, or accounts routes:
        1. Logs the exception.
        2. Cleanly flushes the session so corrupted state is purged from the browser.
        3. Redirects the user directly to the appropriate login page with a friendly notification.
        """
        path = request.path
        logger.critical(f"Unhandled exception on route {path}: {exception}", exc_info=True)

        # Only intercept crashes on management, CMS, accounts, and admin areas
        if path.startswith('/cms/') or path.startswith('/management/department/'):
            self._safe_flush_session(request)
            messages.error(request, "A system or session error occurred. Please log in again.")
            return redirect('management:portal')

        elif path.startswith('/management/'):
            self._safe_flush_session(request)
            messages.error(request, "A session error occurred. Please log in again.")
            return redirect('management:login')

        elif path.startswith('/accounts/'):
            self._safe_flush_session(request)
            messages.error(request, "A session error occurred. Please log in again.")
            return redirect('accounts:login')

        elif path.startswith('/admin/'):
            self._safe_flush_session(request)
            return redirect('/admin/login/')

        return None

    def _safe_flush_session(self, request):
        """Cleanly wipe out session from backend and invalidate cookie."""
        try:
            if hasattr(request, 'user') and request.user.is_authenticated:
                auth_logout(request)
            request.session.flush()
        except Exception:
            request.session.clear()

    def _clear_dept_session_keys(self, request):
        """Clear only department session keys."""
        try:
            request.session.pop('department_account_id', None)
            request.session.pop('department_id', None)
            request.session.pop('department_name', None)
            request.session.pop('department_login_id', None)
            request.session.pop('department_slug', None)
        except Exception:
            pass
