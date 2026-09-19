from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.core.models import ManagementDepartment, DepartmentAccount

User = get_user_model()


class DepartmentAccountModelTest(TestCase):
    def setUp(self):
        self.dept = ManagementDepartment.objects.create(
            name="Content Management System",
            slug="cms",
            code="cms",
            description="Manages store content and banners",
            icon="layout",
            display_order=1
        )

    def test_create_department_account_and_password_hashing(self):
        account = DepartmentAccount.objects.create(
            department=self.dept,
            login_id="CMS001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        account.set_password("SecretPass123!")
        account.save()

        # Password must be hashed, never plain
        self.assertNotEqual(account.password_hash, "SecretPass123!")
        self.assertTrue(account.password_hash.startswith("pbkdf2_") or "argon2" in account.password_hash or "bcrypt" in account.password_hash or "$" in account.password_hash)
        
        # Check password verification
        self.assertTrue(account.check_password("SecretPass123!"))
        self.assertFalse(account.check_password("WrongPassword"))
        self.assertTrue(account.is_active)

    def test_login_id_uniqueness(self):
        DepartmentAccount.objects.create(
            department=self.dept,
            login_id="CMS001",
            password_hash="somehash",
            status=DepartmentAccount.STATUS_ACTIVE
        )

        dept2 = ManagementDepartment.objects.create(
            name="Inventory Management",
            slug="inventory",
            code="inventory",
            description="Manages warehouses and inventory stock",
            icon="package",
            display_order=2
        )

        with self.assertRaises(Exception):
            DepartmentAccount.objects.create(
                department=dept2,
                login_id="CMS001",
                password_hash="somehash2",
                status=DepartmentAccount.STATUS_ACTIVE
            )


class DepartmentAccountSuperadminViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="admin",
            email="admin@cartivo.local",
            password="AdminPassword123!"
        )
        self.regular_user = User.objects.create_user(
            username="regular",
            email="regular@cartivo.local",
            password="UserPassword123!"
        )
        self.dept = ManagementDepartment.objects.create(
            name="Inventory Management",
            slug="inventory",
            code="inventory",
            description="Stock tracking",
            icon="package",
            display_order=1
        )

    def test_department_accounts_view_gating(self):
        url = reverse('management:department_accounts')

        # Anonymous user redirected to login
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

        # Regular user redirected to login
        self.client.login(username="regular", password="UserPassword123!")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

        # Superuser allowed
        self.client.login(username="admin", password="AdminPassword123!")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Inventory Management")
        self.assertContains(res, "Department Accounts Directory")

    def test_configure_department_account(self):
        self.client.login(username="admin", password="AdminPassword123!")
        url = reverse('management:configure_dept_account', kwargs={'dept_id': self.dept.id})

        res = self.client.post(url, {
            'login_id': 'INV001',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'status': DepartmentAccount.STATUS_ACTIVE,
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(DepartmentAccount.objects.filter(department=self.dept, login_id='INV001').exists())
        account = DepartmentAccount.objects.get(department=self.dept)
        self.assertTrue(account.check_password('StrongPassword123!'))
        self.assertEqual(account.status, DepartmentAccount.STATUS_ACTIVE)

    def test_edit_department_login_id(self):
        account = DepartmentAccount.objects.create(
            department=self.dept,
            login_id="INV001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        account.set_password("SomePassword123!")
        account.save()

        self.client.login(username="admin", password="AdminPassword123!")
        url = reverse('management:edit_dept_login_id', kwargs={'dept_id': self.dept.id})

        res = self.client.post(url, {'login_id': 'INV999'}, follow=True)
        self.assertEqual(res.status_code, 200)
        account.refresh_from_db()
        self.assertEqual(account.login_id, 'INV999')

    def test_reset_department_password(self):
        account = DepartmentAccount.objects.create(
            department=self.dept,
            login_id="INV001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        account.set_password("OldPassword123!")
        account.save()

        self.client.login(username="admin", password="AdminPassword123!")
        url = reverse('management:reset_dept_password', kwargs={'dept_id': self.dept.id})

        res = self.client.post(url, {
            'password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!',
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        account.refresh_from_db()
        self.assertTrue(account.check_password('NewPassword123!'))
        self.assertFalse(account.check_password('OldPassword123!'))

    def test_change_department_status(self):
        account = DepartmentAccount.objects.create(
            department=self.dept,
            login_id="INV001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        account.set_password("Pass123!")
        account.save()

        self.client.login(username="admin", password="AdminPassword123!")

        # Suspend
        url_suspend = reverse('management:change_dept_status', kwargs={'dept_id': self.dept.id, 'new_status': 'SUSPENDED'})
        self.client.get(url_suspend)
        account.refresh_from_db()
        self.assertEqual(account.status, DepartmentAccount.STATUS_SUSPENDED)

        # Deactivate
        url_inactive = reverse('management:change_dept_status', kwargs={'dept_id': self.dept.id, 'new_status': 'INACTIVE'})
        self.client.get(url_inactive)
        account.refresh_from_db()
        self.assertEqual(account.status, DepartmentAccount.STATUS_INACTIVE)

        # Re-activate
        url_active = reverse('management:change_dept_status', kwargs={'dept_id': self.dept.id, 'new_status': 'ACTIVE'})
        self.client.get(url_active)
        account.refresh_from_db()
        self.assertEqual(account.status, DepartmentAccount.STATUS_ACTIVE)


class DepartmentStaffAuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = ManagementDepartment.objects.create(
            name="CMS Department",
            slug="cms",
            code="cms",
            description="Content management",
            icon="layout",
            display_order=1
        )
        self.account = DepartmentAccount.objects.create(
            department=self.dept,
            login_id="CMS001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        self.account.set_password("CMSPassword123!")
        self.account.save()
        self.login_url = reverse('management:dept_login')

    def test_successful_active_department_login(self):
        res = self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.client.session.get('department_login_id'), 'CMS001')
        self.assertEqual(self.client.session.get('department_name'), 'CMS Department')
        self.account.refresh_from_db()
        self.assertIsNotNone(self.account.last_login)

    def test_suspended_department_login_error_message(self):
        self.account.status = DepartmentAccount.STATUS_SUSPENDED
        self.account.save()

        res = self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Your department account has been suspended. Please contact the Super Admin.")
        self.assertIsNone(self.client.session.get('department_login_id'))

    def test_inactive_department_login_error_message(self):
        self.account.status = DepartmentAccount.STATUS_INACTIVE
        self.account.save()

        res = self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Your department account is inactive. Please contact the Super Admin.")
        self.assertIsNone(self.client.session.get('department_login_id'))

    def test_pending_department_login_error_message(self):
        self.account.status = DepartmentAccount.STATUS_PENDING
        self.account.save()

        res = self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Your department account is not active yet. Please contact the Super Admin.")
        self.assertIsNone(self.client.session.get('department_login_id'))

    def test_invalid_credentials_error_message(self):
        res = self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'WrongPassword!',
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Invalid Department Login ID or Password.")
        self.assertIsNone(self.client.session.get('department_login_id'))

    def test_department_logout(self):
        # First log in
        self.client.post(self.login_url, {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        }, follow=True)
        self.assertEqual(self.client.session.get('department_login_id'), 'CMS001')

        # Log out
        res = self.client.get(reverse('management:dept_logout'), follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(self.client.session.get('department_login_id'))


class UniversalSessionSecurityTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.superuser = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@cartivo.local",
            password="SuperPassword123!"
        )

        self.dept = ManagementDepartment.objects.create(
            name="CMS Department",
            slug="cms",
            code="cms",
            is_active=True
        )

        self.account = DepartmentAccount.objects.create(
            department=self.dept,
            login_id="CMS001",
            status=DepartmentAccount.STATUS_ACTIVE
        )
        self.account.set_password("CMSPassword123!")
        self.account.save()

    def test_browser_no_cache_headers_enforced(self):
        # 1. Login page
        res = self.client.get(reverse('management:login'))
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))
        self.assertIn('no-store', res.headers.get('Cache-Control', ''))

        # 2. Portal
        res = self.client.get(reverse('management:portal'))
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))
        self.assertIn('no-store', res.headers.get('Cache-Control', ''))

        # 3. Superadmin dashboard when authenticated
        self.client.login(username="superadmin", password="SuperPassword123!")
        res = self.client.get(reverse('management:dashboard'))
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))
        self.assertIn('no-store', res.headers.get('Cache-Control', ''))

    def test_stale_or_missing_backend_session_flushed_and_redirects(self):
        # Browser sends a session with an ID not in database
        session = self.client.session
        session['department_account_id'] = 999999
        session['department_slug'] = 'cms'
        session.save()

        res = self.client.get(reverse('cms:dashboard'))
        self.assertRedirects(res, reverse('management:portal'))
        # Ensure session was flushed
        self.assertIsNone(self.client.session.get('department_account_id'))

    def test_suspended_account_session_in_browser_redirects_and_flushes(self):
        # Log in first
        self.client.post(reverse('management:dept_login'), {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        })
        self.assertEqual(self.client.session.get('department_account_id'), self.account.id)

        # Admin suspends account in DB while browser keeps cookie
        self.account.status = DepartmentAccount.STATUS_SUSPENDED
        self.account.save()

        res = self.client.get(reverse('cms:dashboard'))
        self.assertRedirects(res, reverse('management:portal'))
        self.assertIsNone(self.client.session.get('department_account_id'))

    def test_deleted_account_session_in_browser_redirects_and_flushes(self):
        # Log in first
        self.client.post(reverse('management:dept_login'), {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        })
        self.assertEqual(self.client.session.get('department_account_id'), self.account.id)

        # Account is deleted from database
        self.account.delete()

        res = self.client.get(reverse('cms:dashboard'))
        self.assertRedirects(res, reverse('management:portal'))
        self.assertIsNone(self.client.session.get('department_account_id'))

    def test_crash_exception_recovery_flushes_session_and_redirects_to_login(self):
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from apps.core.middleware import UniversalSessionSecurityMiddleware

        factory = RequestFactory()

        # 1. Test CMS route crash recovery -> redirects to management portal
        request = factory.get('/cms/dashboard/')
        SessionMiddleware(lambda req: None).process_request(request)
        MessageMiddleware(lambda req: None).process_request(request)
        request.session['department_account_id'] = self.account.id
        request.session['department_slug'] = 'cms'
        request.session.save()

        def crashing_cms_view(req):
            raise RuntimeError("Simulated CMS crash")

        middleware = UniversalSessionSecurityMiddleware(crashing_cms_view)
        response = middleware(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('management:portal'))
        self.assertIsNone(request.session.get('department_account_id'))

        # 2. Test Superadmin route crash recovery -> redirects to superadmin login
        admin_req = factory.get('/management/dashboard/')
        SessionMiddleware(lambda req: None).process_request(admin_req)
        MessageMiddleware(lambda req: None).process_request(admin_req)
        admin_req.user = self.superuser

        def crashing_admin_view(req):
            raise RuntimeError("Simulated admin crash")

        admin_middleware = UniversalSessionSecurityMiddleware(crashing_admin_view)
        admin_response = admin_middleware(admin_req)
        self.assertEqual(admin_response.status_code, 302)
        self.assertEqual(admin_response.url, reverse('management:login'))
        self.assertFalse(admin_req.session.keys())

    def test_settings_session_expire_at_browser_close_enabled(self):
        from django.conf import settings
        self.assertTrue(getattr(settings, 'SESSION_EXPIRE_AT_BROWSER_CLOSE', False))

    def test_superadmin_accessing_management_page_redirects_directly_to_dashboard(self):
        self.client.login(username="superadmin", password="SuperPassword123!")
        res = self.client.get(reverse('management:portal'))
        self.assertRedirects(res, reverse('management:dashboard'))

    def test_cms_staff_accessing_management_page_redirects_directly_to_cms_dashboard(self):
        self.client.post(reverse('management:dept_login'), {
            'login_id': 'CMS001',
            'password': 'CMSPassword123!',
        })
        res = self.client.get(reverse('management:portal'))
        self.assertRedirects(res, reverse('cms:dashboard'))

    def test_superadmin_login_direct_redirect_to_dashboard_and_browser_close_expiry(self):
        res = self.client.post(reverse('management:login'), {
            'username': 'superadmin',
            'password': 'SuperPassword123!',
        })
        self.assertRedirects(res, reverse('management:dashboard'))
        # Session should expire at browser close
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_superadmin_session_active_banner_removed_from_portal(self):
        # Even on anonymous view of portal, verify no "Super Administrator Session Active" banner exists
        res = self.client.get(reverse('management:portal'))
        self.assertEqual(res.status_code, 200)
        self.assertNotContains(res, "Super Administrator Session Active")
        self.assertNotContains(res, "ROOT GOVERNANCE ACCESS")


