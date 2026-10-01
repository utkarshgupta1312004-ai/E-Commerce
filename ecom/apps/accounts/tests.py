from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomerAccountsSecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="customer_test",
            email="customer@cartivo.local",
            password="CustomerPassword123!"
        )

    def test_login_page_no_cache_headers(self):
        res = self.client.get(reverse('accounts:login'))
        self.assertEqual(res.status_code, 200)
        self.assertIn('no-cache', res.headers.get('Cache-Control', ''))
        self.assertIn('no-store', res.headers.get('Cache-Control', ''))

    def test_logout_flushes_session(self):
        self.client.login(username="customer_test", password="CustomerPassword123!")
        res = self.client.get(reverse('accounts:logout'), follow=False)
        self.assertEqual(res.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_user_session_redirects_and_flushes(self):
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from apps.core.middleware import UniversalSessionSecurityMiddleware

        factory = RequestFactory()
        req = factory.get('/accounts/dashboard/')
        SessionMiddleware(lambda r: None).process_request(req)
        MessageMiddleware(lambda r: None).process_request(req)
        req.user = self.user
        req.user.is_active = False

        middleware = UniversalSessionSecurityMiddleware(lambda r: None)
        res = middleware(req)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('accounts:login'))
        self.assertFalse(req.session.keys())


class GoogleAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.test_client_id = "test-client-id-12345.apps.googleusercontent.com"

    def post_with_csrf(self, url, data=None):
        data = data.copy() if data else {}
        login_res = self.client.get(reverse('accounts:login'))
        csrf_token = login_res.cookies.get('csrftoken')
        if csrf_token:
            data['csrfmiddlewaretoken'] = csrf_token.value
        return self.client.post(url, data)

    def test_coop_header_allows_popups(self):
        """Verify Cross-Origin-Opener-Policy allows external OAuth popups."""
        res = self.client.get(reverse('accounts:login'))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Cross-Origin-Opener-Policy'), 'same-origin-allow-popups')

    def test_google_login_redirects_to_login_page(self):
        """Verify /accounts/google/login/ redirects to the customer login view."""
        res = self.client.get(reverse('accounts:google_login'))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.url.startswith(reverse('accounts:login')))

    def test_google_callback_rejects_missing_csrf(self):
        """POST request without valid CSRF token must be rejected with HTTP 403."""
        res = self.client.post(reverse('accounts:google_callback'), {'credential': 'fake_token'})
        self.assertEqual(res.status_code, 403)

    def test_google_callback_rejects_get(self):
        """GET request to callback must be rejected and redirected to login."""
        res = self.client.get(reverse('accounts:google_callback'))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('accounts:login'))

    def test_google_callback_rejects_missing_credential(self):
        """POST request without credential must be rejected cleanly."""
        res = self.post_with_csrf(reverse('accounts:google_callback'), {})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse('accounts:login'))

    def test_google_callback_rejects_unconfigured_client_id(self):
        """Callback must fail gracefully if GOOGLE_CLIENT_ID is unset."""
        from unittest.mock import patch
        with patch('apps.accounts.views._get_env_config', return_value=''):
            res = self.post_with_csrf(reverse('accounts:google_callback'), {'credential': 'fake_token'})
            self.assertEqual(res.status_code, 302)
            self.assertEqual(res.url, reverse('accounts:login'))

    def test_google_callback_verification_failure_handled(self):
        """ValueError during verify_oauth2_token must be caught gracefully without crashing."""
        from unittest.mock import patch
        with patch('apps.accounts.views._get_env_config', return_value=self.test_client_id):
            with patch('apps.accounts.views.id_token.verify_oauth2_token', side_effect=ValueError("Token expired")):
                res = self.post_with_csrf(reverse('accounts:google_callback'), {'credential': 'expired_token'})
                self.assertEqual(res.status_code, 302)
                self.assertEqual(res.url, reverse('accounts:login'))

    def test_google_callback_invalid_issuer_rejected(self):
        """Token with invalid issuer must be rejected."""
        from unittest.mock import patch
        mock_idinfo = {
            'iss': 'https://attacker.com',
            'sub': '123456789',
            'email': 'hacker@example.com',
            'email_verified': True,
        }
        with patch('apps.accounts.views._get_env_config', return_value=self.test_client_id):
            with patch('apps.accounts.views.id_token.verify_oauth2_token', return_value=mock_idinfo):
                res = self.post_with_csrf(reverse('accounts:google_callback'), {'credential': 'valid_token_bad_iss'})
                self.assertEqual(res.status_code, 302)
                self.assertEqual(res.url, reverse('accounts:login'))

    def test_google_callback_new_user_registration_success(self):
        """Valid token for new user creates user in Customer group and logs in."""
        from unittest.mock import patch
        mock_idinfo = {
            'iss': 'https://accounts.google.com',
            'sub': 'google-uid-1001',
            'email': 'newcustomer@cartivo.local',
            'email_verified': True,
            'given_name': 'Jane',
            'family_name': 'Doe',
        }
        with patch('apps.accounts.views._get_env_config', return_value=self.test_client_id):
            with patch('apps.accounts.views.id_token.verify_oauth2_token', return_value=mock_idinfo):
                res = self.post_with_csrf(reverse('accounts:google_callback'), {'credential': 'valid_token'})
                self.assertEqual(res.status_code, 302)
                self.assertEqual(res.url, '/')

                # Verify user was created
                user = User.objects.filter(email='newcustomer@cartivo.local').first()
                self.assertIsNotNone(user)
                self.assertEqual(user.first_name, 'Jane')
                self.assertEqual(user.last_name, 'Doe')
                self.assertTrue(user.groups.filter(name='Customer').exists())

                # Verify session authentication
                self.assertEqual(str(user.pk), self.client.session.get('_auth_user_id'))

    def test_google_callback_existing_user_login_success(self):
        """Valid token for existing customer updates missing fields and authenticates."""
        from unittest.mock import patch
        existing_user = User.objects.create_user(
            username="existing_user",
            email="existing@cartivo.local",
            first_name="",
            last_name="",
        )
        mock_idinfo = {
            'iss': 'https://accounts.google.com',
            'sub': 'google-uid-1002',
            'email': 'existing@cartivo.local',
            'email_verified': True,
            'given_name': 'Alex',
            'family_name': 'Smith',
        }
        with patch('apps.accounts.views._get_env_config', return_value=self.test_client_id):
            with patch('apps.accounts.views.id_token.verify_oauth2_token', return_value=mock_idinfo):
                res = self.post_with_csrf(reverse('accounts:google_callback'), {'credential': 'valid_token'})
                self.assertEqual(res.status_code, 302)
                self.assertEqual(res.url, '/')

                existing_user.refresh_from_db()
                self.assertEqual(existing_user.first_name, 'Alex')
                self.assertEqual(existing_user.last_name, 'Smith')
                self.assertEqual(str(existing_user.pk), self.client.session.get('_auth_user_id'))

    def test_google_callback_blocks_superuser_storefront_login(self):
        """Super Administrator accounts must not authenticate through customer Google storefront."""
        from unittest.mock import patch
        admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin@cartivo.local",
            password="AdminPassword123!"
        )
        mock_idinfo = {
            'iss': 'https://accounts.google.com',
            'sub': 'google-uid-admin',
            'email': 'admin@cartivo.local',
            'email_verified': True,
        }
        with patch('apps.accounts.views._get_env_config', return_value=self.test_client_id):
            with patch('apps.accounts.views.id_token.verify_oauth2_token', return_value=mock_idinfo):
                res = self.post_with_csrf(reverse('accounts:google_callback'), {'credential': 'admin_token'})
                self.assertEqual(res.status_code, 302)
                self.assertEqual(res.url, reverse('accounts:login'))
                self.assertNotIn('_auth_user_id', self.client.session)


