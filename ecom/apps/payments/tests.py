import hmac
import hashlib
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import Address
from apps.cart.models import Cart, CartItem
from apps.catalog.models import Category, Product
from apps.inventory.models import Warehouse, Stock
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction
from apps.payments.services import RazorpayService, RazorpayServiceException


class RazorpayServiceTests(TestCase):
    """Unit tests for RazorpayService gateway utility methods."""

    def test_configuration_getters(self):
        self.assertTrue(RazorpayService.get_key_id())
        self.assertTrue(RazorpayService.get_key_secret())
        self.assertEqual(RazorpayService.get_currency(), 'INR')
        self.assertTrue(RazorpayService.is_configured())

    def test_mode_detection(self):
        self.assertTrue(RazorpayService.is_test_mode())
        self.assertEqual(RazorpayService.get_mode(), 'TEST')

    @patch('razorpay.Client')
    def test_create_order_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.order.create.return_value = {
            'id': 'order_test_123456',
            'amount': 49900,
            'currency': 'INR',
            'status': 'created',
            'receipt': 'TXN-123',
        }

        order_data = RazorpayService.create_order(
            amount=Decimal('499.00'),
            currency='INR',
            receipt='TXN-123'
        )

        self.assertEqual(order_data['id'], 'order_test_123456')
        self.assertEqual(order_data['amount'], 49900)
        mock_client.order.create.assert_called_once_with(data={
            'amount': 49900,
            'currency': 'INR',
            'receipt': 'TXN-123',
            'notes': {},
        })

    def test_create_order_invalid_amount(self):
        with self.assertRaises(RazorpayServiceException):
            RazorpayService.create_order(amount=Decimal('0.00'))

    @patch('razorpay.Client')
    def test_create_order_auth_failure_handling(self, mock_client_cls):
        from razorpay.errors import BadRequestError
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.order.create.side_effect = BadRequestError("Authentication failed")

        with self.assertRaises(RazorpayServiceException) as ctx:
            RazorpayService.create_order(amount=Decimal('100.00'))
        self.assertEqual(ctx.exception.code, "AUTH_FAILED")

    @patch('razorpay.Client')
    def test_verify_signature_valid(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.utility.verify_payment_signature.return_value = True

        result = RazorpayService.verify_payment_signature(
            razorpay_order_id='order_123',
            razorpay_payment_id='pay_123',
            razorpay_signature='sig_123'
        )
        self.assertTrue(result)

    @patch('razorpay.Client')
    def test_verify_signature_invalid(self, mock_client_cls):
        from razorpay.errors import SignatureVerificationError
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.utility.verify_payment_signature.side_effect = SignatureVerificationError("Mismatch")

        result = RazorpayService.verify_payment_signature(
            razorpay_order_id='order_123',
            razorpay_payment_id='pay_123',
            razorpay_signature='bad_sig'
        )
        self.assertFalse(result)

    def test_verify_webhook_signature(self):
        secret = 'my_test_webhook_secret'
        body = json.dumps({'event': 'payment.captured'}).encode('utf-8')
        valid_signature = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()

        # Valid signature
        self.assertTrue(RazorpayService.verify_webhook_signature(body, valid_signature, secret=secret))

        # Tampered signature
        self.assertFalse(RazorpayService.verify_webhook_signature(body, 'tampered_sig', secret=secret))

        # Missing secret or signature
        self.assertFalse(RazorpayService.verify_webhook_signature(body, '', secret=secret))
        self.assertFalse(RazorpayService.verify_webhook_signature(body, valid_signature, secret=''))


class RazorpayPaymentViewsTests(TestCase):
    """End-to-end integration tests for Razorpay checkout, verification, idempotency, and security."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='rajesh_kumar',
            email='rajesh@cartivo.local',
            password='Password@123'
        )
        self.other_user = User.objects.create_user(
            username='sneha_patel',
            email='sneha@cartivo.local',
            password='Password@123'
        )
        self.client.login(username='rajesh_kumar', password='Password@123')

        self.category = Category.objects.create(name='Acoustics', slug='acoustics')
        self.product = Product.objects.create(
            title='Cartivo Master Headphones',
            slug='cartivo-master-headphones',
            category=self.category,
            base_price=Decimal('1200.00'),
            is_active=True,
            status='ACTIVE'
        )
        self.warehouse = Warehouse.objects.create(
            name='Central Distribution Hub',
            code='WH-TEST-01',
            is_primary=True
        )
        self.stock = Stock.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            on_hand_quantity=10
        )

        self.address = Address.objects.create(
            user=self.user,
            full_name='Rajesh Kumar',
            phone='9876543210',
            street_address='123 Brigade Road',
            city='Bengaluru',
            state='Karnataka',
            postal_code='560001',
            country='India',
            address_type='shipping',
            is_default=True
        )

        self.cart = Cart.objects.create(user=self.user, status='ACTIVE')
        self.cart_item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=1
        )

    @patch('apps.payments.services.RazorpayService.create_order')
    def test_create_razorpay_order_view_success(self, mock_create_order):
        mock_create_order.return_value = {
            'id': 'order_rzp_test_999',
            'amount': 120000,
            'currency': 'INR',
            'status': 'created',
        }

        url = reverse('payments:razorpay_create_order')
        response = self.client.post(url, {
            'address_id': str(self.address.id),
            'customer_notes': 'Please deliver before 5 PM'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['razorpay_order_id'], 'order_rzp_test_999')
        self.assertEqual(data['amount'], 120000)

        # Check transaction in DB
        txn = PaymentTransaction.objects.filter(razorpay_order_id='order_rzp_test_999').first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.user, self.user)
        self.assertEqual(txn.status, 'INITIATED')
        self.assertEqual(txn.amount, Decimal('1200.00'))
        self.assertEqual(txn.shipping_address, self.address)
        self.assertEqual(txn.customer_notes, 'Please deliver before 5 PM')

    def test_create_razorpay_order_empty_cart(self):
        self.cart.items.all().delete()
        url = reverse('payments:razorpay_create_order')
        response = self.client.post(url, {'address_id': str(self.address.id)})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])

    @patch('apps.payments.services.RazorpayService.create_order')
    def test_amount_tampering_ignored(self, mock_create_order):
        """Tests that client cannot tamper with payable amount. Server recalculates from DB."""
        mock_create_order.return_value = {
            'id': 'order_rzp_tamper_test',
            'amount': 120000,
            'currency': 'INR',
            'status': 'created',
        }

        url = reverse('payments:razorpay_create_order')
        # Attacker sends fake manipulated amount of 10 INR
        response = self.client.post(url, {
            'address_id': str(self.address.id),
            'amount': '10.00',
            'total': '10.00'
        })

        self.assertEqual(response.status_code, 200)
        # Server must have called create_order with server-calculated Decimal('1200.00')
        mock_create_order.assert_called_once()
        call_kwargs = mock_create_order.call_args[1]
        self.assertEqual(call_kwargs['amount'], Decimal('1200.00'))

    @patch('apps.payments.services.RazorpayService.create_order')
    def test_duplicate_order_protection(self, mock_create_order):
        """Tests that clicking Pay twice within 15 minutes reuses recent initiated order."""
        mock_create_order.return_value = {
            'id': 'order_rzp_dup_001',
            'amount': 120000,
            'currency': 'INR',
            'status': 'created',
        }

        url = reverse('payments:razorpay_create_order')
        res1 = self.client.post(url, {'address_id': str(self.address.id)})
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.json()['razorpay_order_id'], 'order_rzp_dup_001')

        # Second request should reuse existing transaction and NOT call create_order again
        res2 = self.client.post(url, {'address_id': str(self.address.id)})
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.json()['razorpay_order_id'], 'order_rzp_dup_001')
        self.assertEqual(mock_create_order.call_count, 1)

    @patch('apps.payments.services.RazorpayService.fetch_payment')
    @patch('apps.payments.services.RazorpayService.verify_payment_signature')
    def test_verify_razorpay_payment_success(self, mock_verify, mock_fetch):
        mock_verify.return_value = True
        mock_fetch.return_value = {
            'id': 'pay_test_888',
            'order_id': 'order_rzp_test_777',
            'amount': 120000,
            'method': 'upi',
            'vpa': 'rajesh@upi',
            'bank': 'HDFC',
            'status': 'captured'
        }

        # Create initiated transaction with stored shipping address
        txn = PaymentTransaction.objects.create(
            transaction_id='TXN-20260929-TEST01',
            user=self.user,
            cart=self.cart,
            shipping_address=self.address,
            customer_notes='Handle with care',
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id='order_rzp_test_777'
        )

        url = reverse('payments:razorpay_verify')
        response = self.client.post(url, {
            'razorpay_order_id': 'order_rzp_test_777',
            'razorpay_payment_id': 'pay_test_888',
            'razorpay_signature': 'valid_sig_xyz'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('redirect_url', data)

        # Verify transaction status changed to SUCCESS
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'SUCCESS')
        self.assertEqual(txn.razorpay_payment_id, 'pay_test_888')
        self.assertEqual(txn.method, 'upi')
        self.assertEqual(txn.vpa, 'rajesh@upi')
        self.assertIsNotNone(txn.order)

        # Verify order details
        order = txn.order
        self.assertEqual(order.payment_method, 'RAZORPAY')
        self.assertEqual(order.payment_status, 'PAID')
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.total_amount, Decimal('1200.00'))

        # Verify cart converted
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, 'CONVERTED')

        # Verify stock deducted
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.on_hand_quantity, 9)

    @patch('apps.payments.services.RazorpayService.verify_payment_signature')
    def test_verify_razorpay_payment_invalid_signature(self, mock_verify):
        mock_verify.return_value = False

        txn = PaymentTransaction.objects.create(
            transaction_id='TXN-20260929-TEST02',
            user=self.user,
            cart=self.cart,
            shipping_address=self.address,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id='order_rzp_test_fail'
        )

        url = reverse('payments:razorpay_verify')
        response = self.client.post(url, {
            'razorpay_order_id': 'order_rzp_test_fail',
            'razorpay_payment_id': 'pay_test_bad',
            'razorpay_signature': 'tampered_signature'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])

        txn.refresh_from_db()
        self.assertEqual(txn.status, 'FAILED')
        self.assertEqual(txn.error_code, 'SIGNATURE_VERIFICATION_FAILED')
        self.assertIsNone(txn.order)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.on_hand_quantity, 10)  # Stock untouched

    def test_verify_unauthorized_user_order_forbidden(self):
        """User B cannot verify User A's payment transaction."""
        txn = PaymentTransaction.objects.create(
            transaction_id='TXN-USER-A',
            user=self.user,
            cart=self.cart,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id='order_user_a'
        )

        # Switch client login to other_user
        self.client.login(username='sneha_patel', password='Password@123')
        url = reverse('payments:razorpay_verify')
        response = self.client.post(url, {
            'razorpay_order_id': 'order_user_a',
            'razorpay_payment_id': 'pay_test_1',
            'razorpay_signature': 'sig_1'
        })

        self.assertEqual(response.status_code, 404)

    def test_record_payment_failure_view(self):
        txn = PaymentTransaction.objects.create(
            transaction_id='TXN-FAIL-01',
            user=self.user,
            cart=self.cart,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id='order_fail_01'
        )

        url = reverse('payments:razorpay_payment_failed')
        response = self.client.post(
            url,
            data=json.dumps({
                'razorpay_order_id': 'order_fail_01',
                'reason': 'FAILED',
                'error_code': 'BAD_REQUEST_ERROR',
                'error_description': 'Customer card expired'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'FAILED')
        self.assertEqual(txn.error_code, 'BAD_REQUEST_ERROR')
        self.assertEqual(txn.error_description, 'Customer card expired')

    def test_razorpay_webhook_missing_signature_rejected(self):
        """Webhook without signature header MUST be rejected with HTTP 400."""
        url = reverse('payments:razorpay_webhook')
        response = self.client.post(
            url,
            data=json.dumps({'event': 'payment.captured'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    @patch('apps.payments.services.RazorpayService.verify_webhook_signature')
    def test_razorpay_webhook_invalid_signature_rejected(self, mock_verify):
        mock_verify.return_value = False
        url = reverse('payments:razorpay_webhook')
        response = self.client.post(
            url,
            data=json.dumps({'event': 'payment.captured'}),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='invalid_signature'
        )
        self.assertEqual(response.status_code, 400)

    @patch('apps.payments.services.RazorpayService.verify_webhook_signature')
    def test_razorpay_webhook_payment_captured(self, mock_verify_webhook):
        mock_verify_webhook.return_value = True

        txn = PaymentTransaction.objects.create(
            transaction_id='TXN-20260929-TEST03',
            user=self.user,
            cart=self.cart,
            shipping_address=self.address,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id='order_webhook_001'
        )

        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_999',
                        'order_id': 'order_webhook_001',
                        'method': 'card',
                        'amount': 120000
                    }
                }
            }
        }

        url = reverse('payments:razorpay_webhook')
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='valid_webhook_sig'
        )

        self.assertEqual(response.status_code, 200)
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'SUCCESS')
        self.assertEqual(txn.razorpay_payment_id, 'pay_webhook_999')
        self.assertEqual(txn.method, 'card')
        self.assertIsNotNone(txn.order)
        self.assertEqual(txn.order.payment_status, 'PAID')

    @patch('apps.payments.services.RazorpayService.verify_webhook_signature')
    def test_razorpay_webhook_idempotency_duplicate(self, mock_verify_webhook):
        """Duplicate webhook deliveries must not create duplicate orders."""
        mock_verify_webhook.return_value = True

        txn = PaymentTransaction.objects.create(
            transaction_id='TXN-WEBHOOK-DUP',
            user=self.user,
            cart=self.cart,
            shipping_address=self.address,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='INITIATED',
            razorpay_order_id='order_webhook_dup'
        )

        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_dup_1',
                        'order_id': 'order_webhook_dup',
                        'method': 'upi',
                        'amount': 120000
                    }
                }
            }
        }

        url = reverse('payments:razorpay_webhook')
        # First delivery creates order
        res1 = self.client.post(url, data=json.dumps(payload), content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE='sig')
        self.assertEqual(res1.status_code, 200)
        order_count_1 = Order.objects.count()

        # Second delivery must acknowledge without recreating order
        res2 = self.client.post(url, data=json.dumps(payload), content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE='sig')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(Order.objects.count(), order_count_1)

    def test_payment_receipt_shows_payment_id_and_paid_status(self):
        """Receipt for a paid order must show PAID stamp and Payment ID."""
        order = Order.objects.create(
            order_number='ORD-TEST-PAID-01',
            user=self.user,
            cart=self.cart,
            shipping_name='Rajesh Kumar',
            shipping_street_address='123 Brigade Road',
            shipping_city='Bengaluru',
            shipping_state='Karnataka',
            shipping_postal_code='560001',
            shipping_country='India',
            status='CONFIRMED',
            payment_method='RAZORPAY',
            payment_status='PAID',
            total_amount=Decimal('1200.00')
        )
        PaymentTransaction.objects.create(
            transaction_id='TXN-RECEIPT-01',
            user=self.user,
            order=order,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='SUCCESS',
            razorpay_order_id='order_rec_01',
            razorpay_payment_id='pay_receipt_rec_01',
            method='upi'
        )

        url = reverse('orders:order_receipt', kwargs={'order_number': order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PAID &bull; RECEIVED')
        self.assertContains(response, 'pay_receipt_rec_01')
        self.assertContains(response, 'Official Payment Receipt')

    def test_unpaid_order_receipt_does_not_show_paid(self):
        """Unpaid order receipt must NOT show PAID stamp even if ?type=payment is passed."""
        order = Order.objects.create(
            order_number='ORD-TEST-PENDING-01',
            user=self.user,
            cart=self.cart,
            shipping_name='Rajesh Kumar',
            shipping_street_address='123 Brigade Road',
            shipping_city='Bengaluru',
            shipping_state='Karnataka',
            shipping_postal_code='560001',
            shipping_country='India',
            status='CONFIRMED',
            payment_method='COD',
            payment_status='PENDING',
            total_amount=Decimal('1200.00')
        )

        url = f"{reverse('orders:order_receipt', kwargs={'order_number': order.order_number})}?type=payment"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'PAID &bull; RECEIVED')
        self.assertContains(response, 'PAYMENT PENDING')
        self.assertContains(response, 'Official Order Receipt')

    def test_payment_transactions_history_view(self):
        PaymentTransaction.objects.create(
            transaction_id='TXN-HIST-01',
            user=self.user,
            cart=self.cart,
            amount=Decimal('1200.00'),
            currency='INR',
            gateway='RAZORPAY',
            status='SUCCESS'
        )

        url = reverse('payments:transactions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TXN-HIST-01')
        self.assertContains(response, 'Payment Ledger')
