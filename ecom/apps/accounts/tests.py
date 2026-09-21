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
