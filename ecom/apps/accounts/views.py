import datetime
import json
import os
import urllib.parse
import urllib.request
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login as auth_login,
    logout as auth_logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Role, UserProfile, Address
from apps.core.models import ManagementDepartment


def login_view(request):
    """
    Renders customer authentication login template and authenticates credentials.
    Supports email or username authentication against the Django User database.
    Respects user.is_active status and rotates session key on login.
    """
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('management:dashboard')
        return redirect('/')

    redirect_to = request.POST.get('next') or request.GET.get('next') or '/'

    if request.method == 'POST':
        login_id = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me')

        if not login_id or not password:
            messages.error(request, "Please enter both email/username and password.")
            return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})

        # Try authenticating directly as username first
        user = authenticate(request, username=login_id, password=password)

        # If direct username authentication failed, check if login_id is an email
        if user is None:
            user_by_email = User.objects.filter(email__iexact=login_id).first()
            if user_by_email:
                user = authenticate(request, username=user_by_email.username, password=password)

        # If authenticate returned None, check if user exists with inactive status or superuser
        if user is None:
            candidate = (
                User.objects.filter(username__iexact=login_id).first() or
                User.objects.filter(email__iexact=login_id).first()
            )
            if candidate and candidate.check_password(password):
                if candidate.is_superuser:
                    messages.error(
                        request,
                        "Super Administrator accounts cannot sign in through the customer storefront. Please authenticate via the Management Portal (/management/login/)."
                    )
                    return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})
                if not candidate.is_active:
                    messages.error(
                        request,
                        "Your account has been deactivated or suspended. Please contact customer support."
                    )
                    return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})

        if user is not None:
            # 1. Superadmin accounts are strictly forbidden from customer storefront login
            if user.is_superuser:
                messages.error(
                    request,
                    "Super Administrator accounts cannot sign in through the customer storefront. Please authenticate via the Management Portal (/management/login/)."
                )
                return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})

            # 2. Check active status
            if not user.is_active:
                messages.error(
                    request,
                    "Your account has been deactivated or suspended. Please contact customer support."
                )
                return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})

            # 3. Department staff accounts cannot log in through customer storefront
            is_dept_staff = (
                user.groups.filter(name__in=['Cartivo Department', 'Cartive Department']).exists() or
                hasattr(user, 'department_account')
            )
            if is_dept_staff:
                messages.error(
                    request,
                    "Department staff accounts cannot sign in through the customer storefront. Please use the Management Portal."
                )
                return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})

            # Rotate session key to protect against session fixation
            request.session.cycle_key()

            # Set session expiry to 0: expires on browser or tab close
            request.session.set_expiry(0)

            auth_login(request, user)
            try:
                from apps.cart.services import CartService
                CartService.merge_guest_cart(request, user)
            except Exception:
                pass
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")

            # Ensure redirect is safe
            if redirect_to and redirect_to.startswith('/'):
                return redirect(redirect_to)
            return redirect('/')
        else:
            messages.error(request, "Invalid email/username or password. Please check your credentials.")
            return render(request, 'accounts/login.html', {'next': redirect_to, 'email': login_id})

    return render(request, 'accounts/login.html', {'next': redirect_to})


def register_view(request):
    """
    Customer Registration View (/accounts/register/).
    Registers new customer using existing User model and UserProfile.
    """
    redirect_to = request.POST.get('next') or request.GET.get('next') or '/'

    if request.user.is_authenticated:
        if redirect_to and redirect_to.startswith('/'):
            return redirect(redirect_to)
        return redirect('/')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Basic validations
        errors = []
        if not full_name:
            errors.append("Please provide your full name.")
        if not email:
            errors.append("Please provide an email address.")
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors.append("Please provide a valid email address.")

        if not password:
            errors.append("Password is required.")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters long.")

        if password != confirm_password:
            errors.append("Passwords do not match.")

        if email and User.objects.filter(email__iexact=email).exists():
            errors.append("An account with this email already exists. Please sign in instead.")

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'accounts/register.html', {
                'full_name': full_name,
                'email': email,
                'phone': phone,
            })

        # Name splitting
        parts = full_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        # Unique username generation from email
        username = email
        if User.objects.filter(username=username).exists():
            username = f"{email.split('@')[0]}_{get_random_string(5)}"

        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        # Assign to Customer group
        customer_group, _ = Group.objects.get_or_create(name='Customer')
        user.groups.add(customer_group)

        # Save phone to existing UserProfile
        if hasattr(user, 'profile'):
            user.profile.phone = phone
            user.profile.save()

        # Rotate session key and log in
        request.session.cycle_key()
        auth_login(request, user)
        try:
            from apps.cart.services import CartService
            CartService.merge_guest_cart(request, user)
        except Exception:
            pass
        messages.success(request, f"Welcome to Cartivo, {user.first_name}! Your account has been created.")
        if redirect_to and redirect_to.startswith('/'):
            return redirect(redirect_to)
        return redirect('/')


    return render(request, 'accounts/register.html', {'next': redirect_to})


def _get_env_config(key, default=''):
    """
    Retrieves configuration value from os.environ, falling back to parsing .env file
    from project directory or workspace root if not already in system environment.
    """
    val = os.environ.get(key, '').strip()
    if val:
        return val
    for env_path in [settings.BASE_DIR / '.env', settings.BASE_DIR.parent / '.env']:
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() == key:
                                return v.strip().strip('"').strip("'")
            except Exception:
                pass
    return default


def google_login_view(request):
    """
    Initiates Google OAuth2 login flow.
    Uses GOOGLE_CLIENT_ID from environment variables or .env file.
    """
    client_id = _get_env_config('GOOGLE_CLIENT_ID')
    if not client_id:
        messages.warning(
            request,
            "Google Sign-In is not currently configured. Please sign in using your email and password."
        )
        return redirect('accounts:login')

    redirect_uri = request.build_absolute_uri(reverse('accounts:google_callback'))
    state = get_random_string(32)
    request.session['google_oauth_state'] = state

    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


def google_callback_view(request):
    """
    Handles Google OAuth2 callback.
    Exchanges code for access token and authenticates or registers customer.
    """
    code = request.GET.get('code')
    state = request.GET.get('state')
    saved_state = request.session.pop('google_oauth_state', None)

    if not code or (saved_state and state != saved_state):
        messages.error(request, "Google authentication could not be verified. Please try again.")
        return redirect('accounts:login')

    client_id = _get_env_config('GOOGLE_CLIENT_ID')
    client_secret = _get_env_config('GOOGLE_CLIENT_SECRET')
    redirect_uri = request.build_absolute_uri(reverse('accounts:google_callback'))

    if not client_id or not client_secret:
        messages.error(request, "Google OAuth configuration is incomplete.")
        return redirect('accounts:login')

    try:
        token_url = "https://oauth2.googleapis.com/token"
        token_data = urllib.parse.urlencode({
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }).encode('utf-8')

        token_req = urllib.request.Request(token_url, data=token_data, method='POST')
        token_req.add_header('Content-Type', 'application/x-www-form-urlencoded')

        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token_json = json.loads(resp.read().decode('utf-8'))
            access_token = token_json.get('access_token')

        if not access_token:
            messages.error(request, "Unable to obtain Google access token.")
            return redirect('accounts:login')

        # Fetch Google user info
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        userinfo_req = urllib.request.Request(userinfo_url)
        userinfo_req.add_header('Authorization', f"Bearer {access_token}")

        with urllib.request.urlopen(userinfo_req, timeout=10) as resp:
            user_info = json.loads(resp.read().decode('utf-8'))

        email = user_info.get('email', '').lower()
        if not email:
            messages.error(request, "Google did not provide an email address.")
            return redirect('accounts:login')

        # Existing account?
        user = User.objects.filter(email__iexact=email).first()

        if user:
            if not user.is_active:
                messages.error(request, "Your account has been deactivated. Please contact support.")
                return redirect('accounts:login')
            if user.is_superuser:
                messages.error(
                    request,
                    "Super Administrator accounts cannot sign in through the customer storefront. Please use the Management Portal."
                )
                return redirect('accounts:login')
            is_dept_staff = (
                user.groups.filter(name__in=['Cartivo Department', 'Cartive Department']).exists() or
                hasattr(user, 'department_account')
            )
            if is_dept_staff:
                messages.error(
                    request,
                    "Department staff accounts cannot sign in through the customer storefront. Please use the Management Portal."
                )
                return redirect('accounts:login')
        else:
            # Register new customer
            first_name = user_info.get('given_name', '')
            last_name = user_info.get('family_name', '')
            username = email
            if User.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}_{get_random_string(5)}"

            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            # Make sure unusable password
            user.set_unusable_password()
            user.save()

            # Assign to Customer group
            customer_group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(customer_group)

        request.session.cycle_key()
        auth_login(request, user)
        try:
            from apps.cart.services import CartService
            CartService.merge_guest_cart(request, user)
        except Exception:
            pass
        messages.success(request, f"Signed in with Google as {user.first_name or user.email}.")
        return redirect('/')

    except Exception as e:
        messages.error(request, f"Google authentication failed: {str(e)}")
        return redirect('accounts:login')


@login_required(login_url='/accounts/login/')
def profile_view(request):
    """
    Customer Profile View (/accounts/profile/).
    Displays and allows updating customer account information.
    """
    user = request.user
    profile = getattr(user, 'profile', None)

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()

        # Validate email
        if email != user.email:
            if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
                messages.error(request, "This email is already in use by another account.")
                return render(request, 'accounts/profile.html', {'profile': profile})
            try:
                validate_email(email)
                user.email = email
            except ValidationError:
                messages.error(request, "Please provide a valid email address.")
                return render(request, 'accounts/profile.html', {'profile': profile})

        user.first_name = first_name
        user.last_name = last_name
        user.save()

        if profile:
            profile.phone = phone
            profile.save()

        messages.success(request, "Your profile has been successfully updated.")
        return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'profile': profile,
    })


@login_required(login_url='/accounts/login/')
def change_password_view(request):
    """
    Customer Password Change View (/accounts/password/change/).
    Uses Django's PasswordChangeForm to securely update the customer password.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep session valid
            messages.success(request, "Your password has been successfully updated.")
            return redirect('accounts:profile')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, err)
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required(login_url='/accounts/login/')
def account_settings_view(request):
    """
    Customer Account Settings View (/accounts/settings/).
    Displays account overview, security status, and preferences.
    """
    return render(request, 'accounts/settings.html', {
        'profile': getattr(request.user, 'profile', None),
    })


@csrf_exempt
def logout_view(request):
    """
    Customer / User Logout View (/accounts/logout/).
    Flushes the session completely and invalidates any browser-cached session.
    Supports standard GET/POST redirects as well as Beacon/AJAX terminations on tab/browser close.
    """
    auth_logout(request)
    request.session.flush()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'multipart/form-data':
        return JsonResponse({'status': 'logged_out', 'message': 'Session expired successfully.'})

    messages.info(request, "You have been successfully signed out.")
    return redirect('accounts:login')


# ==============================================================================
# Accounts Department Management Views (/accounts/manage/)
# Gated to Accounts Department Staff & Super Administrators
# ==============================================================================

def _has_accounts_access(request) -> bool:
    """
    Validates if the user is authorized to manage the Accounts department:
    - Super Administrators
    - Department staff authenticated into the 'accounts' department
    - Users with assigned Role or UserProfile department access for 'accounts'
    """
    if not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    if request.session.get('department_slug') == 'accounts':
        return True
    profile = getattr(request.user, 'profile', None)
    if profile and profile.has_department_access('accounts'):
        return True
    return False


def _get_accounts_dept_info(request):
    """
    Constructs operator and department identity metadata for Accounts Studio layout.
    Supports both superadmin, authenticated staff, and department session logins.
    """
    is_superuser = request.user.is_authenticated and request.user.is_superuser
    is_staff = request.user.is_authenticated and request.user.is_staff
    dept_login = request.session.get('department_login_id')

    if dept_login:
        login_id = dept_login
        operator_name = request.session.get('department_name', 'Accounts Staff')
        dept_name = 'Accounts & Governance'
    elif is_superuser:
        login_id = request.user.username.upper()
        operator_name = request.user.get_full_name() or request.user.username
        dept_name = 'Super Administrator'
    elif is_staff:
        login_id = request.user.username.upper()
        operator_name = request.user.get_full_name() or request.user.username
        job_title = getattr(getattr(request.user, 'profile', None), 'job_title', '')
        dept_name = job_title or 'Accounts Staff'
    else:
        login_id = 'ACC_STAFF'
        operator_name = 'Accounts Staff'
        dept_name = 'Identity & Governance'

    return {
        'login_id': login_id,
        'operator_name': operator_name,
        'dept_name': dept_name,
        'is_superuser': is_superuser,
        'is_staff': is_staff,
    }


def accounts_dashboard_view(request):
    """
    Accounts Department Management Console (/accounts/manage/).
    Dashboard shows: Total users, active users, new users, blocked users.
    Provides a searchable, filterable directory with in-app edit options.
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted. Accounts Department staff or Super Administrator credentials required.")
        return redirect('management:portal')

    now = timezone.now()
    thirty_days_ago = now - datetime.timedelta(days=30)

    total_users = User.objects.count()
    customer_count = User.objects.filter(is_staff=False, is_superuser=False).count()
    staff_count = User.objects.filter(is_staff=True, is_superuser=False).count()
    superadmin_count = User.objects.filter(is_superuser=True).count()
    active_users = User.objects.filter(is_active=True).count()
    new_users = User.objects.filter(date_joined__gte=thirty_days_ago).count()
    blocked_users = User.objects.filter(is_active=False).count()

    # Search and Filter query
    q = request.GET.get('q', '').strip()
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')

    users_qs = User.objects.select_related('profile').prefetch_related(
        'groups',
        'addresses',
        'profile__roles',
        'profile__department_access'
    ).order_by('-date_joined')

    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(profile__phone__icontains=q) |
            Q(profile__job_title__icontains=q)
        )

    if role_filter == 'customer':
        users_qs = users_qs.filter(is_staff=False, is_superuser=False)
    elif role_filter == 'staff':
        users_qs = users_qs.filter(is_staff=True, is_superuser=False)
    elif role_filter == 'superuser':
        users_qs = users_qs.filter(is_superuser=True)

    if status_filter == 'active':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'blocked':
        users_qs = users_qs.filter(is_active=False)

    users_list = list(users_qs[:100])

    context = {
        'active_tab': 'users',
        'total_users': total_users,
        'customer_count': customer_count,
        'staff_count': staff_count,
        'superadmin_count': superadmin_count,
        'active_users': active_users,
        'new_users': new_users,
        'blocked_users': blocked_users,
        'users': users_list,
        'users_list': users_list,
        'users_count': total_users,
        'search_query': q,
        'q': q,
        'selected_role': role_filter,
        'role_filter': role_filter,
        'selected_status': status_filter,
        'status_filter': status_filter,
        'dept_info': _get_accounts_dept_info(request),
    }
    return render(request, 'accounts/manage/users.html', context)


def accounts_user_detail_view(request, user_id: int):
    """
    Accounts Department User Detail & In-App Edit Console (/accounts/manage/users/<id>/).
    Enables department staff to edit profiles, roles, credentials, and addresses
    without ever redirecting to Django Administration.
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted to Accounts Department staff.")
        return redirect('management:portal')

    target_user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    addresses = list(target_user.addresses.all())
    all_roles = list(Role.objects.all())
    all_departments = list(ManagementDepartment.objects.filter(is_active=True))

    if request.method == 'POST':
        action = request.POST.get('action', 'update_profile')

        if action == 'update_profile':
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip().lower()
            phone = (request.POST.get('phone_number') or request.POST.get('phone', '')).strip()
            job_title = request.POST.get('job_title', '').strip()
            account_type = request.POST.get('account_type', '')
            is_active = request.POST.get('is_active') in ('on', 'true', '1')

            # Flexible role resolution
            if account_type == 'staff':
                is_staff = True
            elif account_type == 'customer':
                is_staff = False
            else:
                is_staff = request.POST.get('is_staff') in ('on', 'true', '1')

            is_management_staff = is_staff or (request.POST.get('is_management_staff') in ('on', 'true', '1'))

            if not username:
                messages.error(request, "Username cannot be empty.")
                return redirect('accounts:user_detail', user_id=user_id)

            if User.objects.filter(username=username).exclude(id=target_user.id).exists():
                messages.error(request, f"Username '{username}' is already taken.")
                return redirect('accounts:user_detail', user_id=user_id)

            if email and User.objects.filter(email__iexact=email).exclude(id=target_user.id).exists():
                messages.error(request, f"Email '{email}' is already associated with another account.")
                return redirect('accounts:user_detail', user_id=user_id)

            target_user.username = username
            target_user.first_name = first_name
            target_user.last_name = last_name
            target_user.email = email
            target_user.is_active = is_active
            target_user.is_staff = is_staff
            target_user.save()

            # Synchronize group memberships
            if is_staff:
                dept_group, _ = Group.objects.get_or_create(name='Cartivo Department')
                target_user.groups.add(dept_group)
                cust_group = Group.objects.filter(name='Customer').first()
                if cust_group:
                    target_user.groups.remove(cust_group)
            else:
                cust_group, _ = Group.objects.get_or_create(name='Customer')
                target_user.groups.add(cust_group)
                for g in Group.objects.filter(name__in=['Cartivo Department', 'Cartive Department']):
                    target_user.groups.remove(g)

            profile.phone = phone
            profile.job_title = job_title
            profile.is_management_staff = is_management_staff

            # Update Roles & Department Access
            role_val = request.POST.get('role')
            role_vals = request.POST.getlist('roles')
            all_role_candidates = ([role_val] if role_val else []) + role_vals
            if all_role_candidates:
                profile.roles.set(Role.objects.filter(
                    Q(id__in=[v for v in all_role_candidates if str(v).isdigit()]) |
                    Q(code__in=all_role_candidates)
                ))
            else:
                profile.roles.clear()

            dept_vals = request.POST.getlist('department_access') or request.POST.getlist('departments')
            if dept_vals:
                profile.department_access.set(ManagementDepartment.objects.filter(
                    Q(slug__in=dept_vals) |
                    Q(id__in=[v for v in dept_vals if str(v).isdigit()])
                ))
            else:
                profile.department_access.clear()

            profile.save()

            messages.success(request, f"Account details for '{target_user.username}' updated successfully.")
            return redirect('accounts:user_detail', user_id=user_id)

        elif action == 'reset_password':
            new_password = request.POST.get('new_password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()

            if not new_password or len(new_password) < 6:
                messages.error(request, "Password must be at least 6 characters long.")
                return redirect('accounts:user_detail', user_id=user_id)

            if new_password != confirm_password:
                messages.error(request, "New password and confirmation do not match.")
                return redirect('accounts:user_detail', user_id=user_id)

            target_user.set_password(new_password)
            target_user.save()
            messages.success(request, f"Password reset successfully for '{target_user.username}'.")
            return redirect('accounts:user_detail', user_id=user_id)

    user_dept_access = list(profile.department_access.values_list('slug', flat=True))
    context = {
        'active_tab': 'users',
        'target_user': target_user,
        'profile': profile,
        'addresses': addresses,
        'roles': all_roles,
        'all_roles': all_roles,
        'all_departments': all_departments,
        'user_dept_access': user_dept_access,
        'dept_info': _get_accounts_dept_info(request),
    }
    return render(request, 'accounts/manage/user_detail.html', context)


def accounts_user_add_view(request):
    """
    In-app Account Creation View (/accounts/manage/users/add/).
    Allows Accounts staff to create customers or staff accounts directly
    without accessing the Django Administration interface.
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted to Accounts Department staff.")
        return redirect('management:portal')

    all_roles = list(Role.objects.all())
    all_departments = list(ManagementDepartment.objects.filter(is_active=True))

    if request.method == 'POST':
        account_type = request.POST.get('account_type', 'customer')
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        phone = (request.POST.get('phone_number') or request.POST.get('phone', '')).strip()
        job_title = request.POST.get('job_title', '').strip()

        if not username:
            messages.error(request, "Username is required.")
            return redirect('accounts:user_add')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('accounts:user_add')

        if email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, f"Email '{email}' is already registered.")
            return redirect('accounts:user_add')

        if not password or len(password) < 6:
            messages.error(request, "Password must be at least 6 characters.")
            return redirect('accounts:user_add')

        is_staff = (request.POST.get('is_staff') in ('on', 'true', '1') or account_type == 'staff')
        is_active = (request.POST.get('is_active', 'on') in ('on', 'true', '1'))

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=is_staff,
        )
        if not is_active:
            user.is_active = False
            user.save(update_fields=['is_active'])

        if is_staff:
            dept_group, _ = Group.objects.get_or_create(name='Cartivo Department')
            user.groups.add(dept_group)
        else:
            cust_group, _ = Group.objects.get_or_create(name='Customer')
            user.groups.add(cust_group)

        if hasattr(user, 'profile'):
            user.profile.phone = phone
            user.profile.job_title = job_title
            user.profile.is_management_staff = is_staff

            role_val = request.POST.get('role')
            role_vals = request.POST.getlist('roles')
            all_role_candidates = ([role_val] if role_val else []) + role_vals
            if all_role_candidates:
                user.profile.roles.set(Role.objects.filter(
                    Q(id__in=[v for v in all_role_candidates if str(v).isdigit()]) |
                    Q(code__in=all_role_candidates)
                ))

            dept_vals = request.POST.getlist('department_access') or request.POST.getlist('departments')
            if dept_vals:
                user.profile.department_access.set(ManagementDepartment.objects.filter(
                    Q(slug__in=dept_vals) |
                    Q(id__in=[v for v in dept_vals if str(v).isdigit()])
                ))

            user.profile.save()

        messages.success(request, f"Account '{user.username}' created successfully.")
        return redirect('accounts:user_detail', user_id=user.id)

    context = {
        'active_tab': 'user_add',
        'roles': all_roles,
        'all_roles': all_roles,
        'all_departments': all_departments,
        'dept_info': _get_accounts_dept_info(request),
    }
    return render(request, 'accounts/manage/user_add.html', context)


def accounts_user_toggle_status_view(request, user_id: int):
    """
    1-Click User Active/Blocked Status Toggle (/accounts/manage/users/<id>/toggle-status/).
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    target_user = get_object_or_404(User, id=user_id)
    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, "Only Super Administrators can modify Superadmin accounts.")
        return redirect('accounts:dashboard')

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    # Synchronize department account status if linked
    if hasattr(target_user, 'department_account'):
        dept_acc = target_user.department_account
        from apps.core.models import DepartmentAccount
        dept_acc.status = DepartmentAccount.STATUS_ACTIVE if target_user.is_active else DepartmentAccount.STATUS_SUSPENDED
        dept_acc.save(update_fields=['status'])

    state_label = "Activated" if target_user.is_active else "Blocked"
    messages.success(request, f"Account '{target_user.username}' has been {state_label}.")
    return redirect(request.META.get('HTTP_REFERER') or 'accounts:dashboard')


def accounts_address_add_view(request, user_id: int):
    """
    Adds a customer address directly from the User Detail console.
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    target_user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        street_address = request.POST.get('street_address', '').strip()
        apartment = request.POST.get('apartment', '').strip()
        city = request.POST.get('city', '').strip()
        state = request.POST.get('state', '').strip()
        postal_code = request.POST.get('postal_code', '').strip()
        country = request.POST.get('country', 'United States').strip()
        address_type = request.POST.get('address_type', 'shipping')
        is_default = request.POST.get('is_default') == 'on'

        if not full_name or not street_address or not city or not postal_code:
            messages.error(request, "Please fill in all required address fields.")
            return redirect('accounts:user_detail', user_id=user_id)

        Address.objects.create(
            user=target_user,
            full_name=full_name,
            phone=phone,
            street_address=street_address,
            apartment=apartment,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            address_type=address_type,
            is_default=is_default
        )
        messages.success(request, f"Address added successfully for '{target_user.username}'.")

    return redirect('accounts:user_detail', user_id=user_id)


def accounts_address_delete_view(request, user_id: int, address_id: int):
    """
    Deletes an address directly from the User Detail console.
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    address = get_object_or_404(Address, id=address_id, user_id=user_id)
    address.delete()
    messages.success(request, "Address deleted successfully.")
    return redirect('accounts:user_detail', user_id=user_id)


def accounts_roles_view(request):
    """
    Accounts Department Roles & Permissions Registry (/accounts/manage/roles/).
    Allows viewing, creating, and updating management roles without Django Admin.
    """
    if not _has_accounts_access(request):
        messages.error(request, "Access restricted.")
        return redirect('management:portal')

    roles_list = list(Role.objects.prefetch_related('departments', 'permissions').all())
    all_departments = list(ManagementDepartment.objects.filter(is_active=True))

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        description = request.POST.get('description', '').strip()
        is_superadmin = request.POST.get('is_superadmin') == 'on'

        if not name or not code:
            messages.error(request, "Role name and code are required.")
            return redirect('accounts:roles')

        from django.utils.text import slugify
        slug_code = slugify(code)

        if Role.objects.filter(code=slug_code).exists():
            messages.error(request, f"Role code '{slug_code}' already exists.")
            return redirect('accounts:roles')

        role = Role.objects.create(
            name=name,
            code=slug_code,
            description=description,
            is_superadmin=is_superadmin and request.user.is_superuser
        )

        dept_ids = request.POST.getlist('departments')
        if dept_ids:
            role.departments.set(ManagementDepartment.objects.filter(id__in=dept_ids))

        messages.success(request, f"Role '{role.name}' created successfully.")
        return redirect('accounts:roles')

    context = {
        'active_tab': 'roles',
        'roles_list': roles_list,
        'all_departments': all_departments,
        'dept_info': _get_accounts_dept_info(request),
    }
    return render(request, 'accounts/manage/roles.html', context)


