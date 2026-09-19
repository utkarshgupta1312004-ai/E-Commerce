from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.accounts.models import Address
from apps.catalog.models import Category, Brand, Product, ProductVariant
from apps.inventory.models import Warehouse, Stock, StockMovement
from apps.inventory.services import InventoryService
from django.utils import timezone
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem, DeliveryCheckpoint
from apps.orders.services import OrderService


class OrderCODIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='customer1@cartivo.com',
            email='customer1@cartivo.com',
            password='Password@123',
            first_name='Alex',
            last_name='Morgan'
        )
        self.other_user = User.objects.create_user(
            username='customer2@cartivo.com',
            email='customer2@cartivo.com',
            password='Password@123',
            first_name='Bob',
            last_name='Jones'
        )

        self.address = Address.objects.create(
            user=self.user,
            full_name='Alex Morgan',
            phone='9876543210',
            street_address='452 Fifth Avenue',
            apartment='Suite 12B',
            city='New York',
            state='NY',
            postal_code='10018',
            country='United States',
            address_type='shipping',
            is_default=True
        )

        self.category = Category.objects.create(name='Smartphones', slug='smartphones')
        self.brand = Brand.objects.create(name='Horizon', slug='horizon')
        self.warehouse = Warehouse.objects.create(name='Main Hub', code='WH-MAIN', is_primary=True)

        # Standalone Product (Stock: 10)
        self.phone = Product.objects.create(
            title='Horizon Edge Ultra 5G',
            slug='horizon-edge-ultra-5g',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('899.00'),
            sku='HRZ-ULTRA-5G',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )
        stk = InventoryService.get_or_create_stock(self.phone, self.warehouse)
        stk.on_hand_quantity = 10
        stk.status = 'IN_STOCK'
        stk.save()

        # Variable Product (Stock: 3)
        self.case = Product.objects.create(
            title='Leather Protective Case',
            slug='leather-protective-case',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('49.00'),
            product_type='variable',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )
        self.case_variant = ProductVariant.objects.create(
            product=self.case,
            sku='CASE-MIDNIGHT',
            name='Midnight Black',
            price=Decimal('49.00')
        )
        stk_case = InventoryService.get_or_create_stock(self.case, self.warehouse, variant=self.case_variant)
        stk_case.on_hand_quantity = 3
        stk_case.status = 'IN_STOCK'
        stk_case.save()

    def test_10_user_reaches_checkout(self):
        """TEST 10: Authenticated user reaches checkout with active cart items."""
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        
        # Add phone to cart
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)

        response = self.client.get('/checkout/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Horizon Edge Ultra 5G')
        self.assertContains(response, '452 Fifth Avenue')
        self.assertContains(response, 'Cash on Delivery (COD)')

    def test_11_user_selects_cash_on_delivery(self):
        """TEST 11: Checkout page presents Cash on Delivery as active payment method."""
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)

        response = self.client.get('/checkout/')
        self.assertContains(response, 'name="payment_method"')
        self.assertContains(response, 'value="COD"')

    def test_12_user_confirms_cod_order_complete_flow(self):
        """
        TEST 12: User confirms order.
        Expected:
        - Order created
        - OrderItems created
        - COD payment status = PENDING
        - Order status = CONFIRMED
        - Inventory updated (10 -> 8)
        - StockMovement created with reference = order_number
        - Cart converted (ACTIVE -> CONVERTED)
        - Success page displayed
        """
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=2)

        initial_stock = Stock.objects.get(product=self.phone, warehouse=self.warehouse).on_hand_quantity
        self.assertEqual(initial_stock, 10)

        response = self.client.post('/checkout/place-order/', {
            'address_id': self.address.id,
            'payment_method': 'COD',
            'customer_notes': 'Please call before delivery',
        }, follow=True)

        self.assertEqual(response.status_code, 200)

        # 1. Order created
        order = Order.objects.filter(user=self.user).first()
        self.assertIsNotNone(order)
        self.assertTrue(order.order_number.startswith('ORD-'))
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.payment_method, 'COD')
        self.assertEqual(order.payment_status, 'PENDING')
        self.assertEqual(order.total_amount, Decimal('1798.00'))  # 2 * 899.00
        self.assertEqual(order.shipping_street_address, '452 Fifth Avenue')

        # 2. OrderItems created with historical snapshot
        items = list(order.items.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].sku, 'HRZ-ULTRA-5G')
        self.assertEqual(items[0].product_title, 'Horizon Edge Ultra 5G')
        self.assertEqual(items[0].quantity, 2)
        self.assertEqual(items[0].unit_price, Decimal('899.00'))
        self.assertEqual(items[0].subtotal, Decimal('1798.00'))

        # 3. Inventory updated
        updated_stock = Stock.objects.get(product=self.phone, warehouse=self.warehouse).on_hand_quantity
        self.assertEqual(updated_stock, 8)

        # 4. StockMovement created
        movement = StockMovement.objects.filter(reference_id=order.order_number).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.movement_type, 'SALE')
        self.assertEqual(movement.quantity, -2)

        # 5. Cart converted
        cart.refresh_from_db()
        self.assertEqual(cart.status, 'CONVERTED')

        # 6. Success page displayed
        self.assertContains(response, 'Order Placed Successfully')
        self.assertContains(response, order.order_number)

    def test_13_insufficient_stock_fails_atomically(self):
        """
        TEST 13: Insufficient stock.
        Expected: Order NOT created, Inventory unchanged, Cart remains ACTIVE.
        """
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        # Only 3 cases in stock; customer requests 5
        CartItem.objects.create(cart=cart, product=self.case, variant=self.case_variant, quantity=5)

        response = self.client.post('/checkout/place-order/', {
            'address_id': self.address.id,
            'payment_method': 'COD',
        }, follow=True)

        # Order must NOT be created
        self.assertEqual(Order.objects.count(), 0)

        # Stock must remain intact
        stk = Stock.objects.get(product=self.case, variant=self.case_variant)
        self.assertEqual(stk.on_hand_quantity, 3)

        # Cart must remain ACTIVE
        cart.refresh_from_db()
        self.assertEqual(cart.status, 'ACTIVE')

        # Error notification shown
        self.assertContains(response, 'Unable to place order due to stock shortage')

    def test_14_customer_cannot_access_another_customers_order(self):
        """
        TEST 14: Customer attempts to access another customer's order.
        Expected: 404 Not Found.
        """
        # Create order for user 1
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)
        order = OrderService.create_cod_order(user=self.user, address=self.address)

        # Login as user 2
        self.client.login(username='customer2@cartivo.com', password='Password@123')

        # Attempt to access user 1's order
        res_detail = self.client.get(f"/orders/{order.order_number}/")
        self.assertEqual(res_detail.status_code, 404)

        res_success = self.client.get(f"/orders/success/{order.order_number}/")
        self.assertEqual(res_success.status_code, 404)

        res_receipt = self.client.get(f"/orders/{order.order_number}/receipt/")
        self.assertEqual(res_receipt.status_code, 404)

    def test_15_refresh_order_success_page_does_not_create_duplicate(self):
        """
        TEST 15: Refresh order success page.
        Expected: Does NOT create another order.
        """
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)
        order = OrderService.create_cod_order(user=self.user, address=self.address)

        self.assertEqual(Order.objects.count(), 1)

        # Refresh success page twice
        self.client.get(f"/orders/success/{order.order_number}/")
        self.client.get(f"/orders/success/{order.order_number}/")

        self.assertEqual(Order.objects.count(), 1)

    def test_16_customer_opens_my_orders(self):
        """
        TEST 16: Customer opens My Orders.
        Expected: New COD order appears in list.
        """
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)
        order = OrderService.create_cod_order(user=self.user, address=self.address)

        response = self.client.get('/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)
        self.assertContains(response, 'Cash on Delivery')
        self.assertContains(response, 'Pending')

    def test_17_customer_opens_order_detail(self):
        """
        TEST 17: Customer opens order detail.
        Expected: All order information, items, address, and status visible.
        """
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)
        order = OrderService.create_cod_order(user=self.user, address=self.address)

        response = self.client.get(f"/orders/{order.order_number}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, order.order_number)
        self.assertContains(response, 'Horizon Edge Ultra 5G')
        self.assertContains(response, '452 Fifth Avenue')
        self.assertContains(response, 'Pending')

    def test_18_customer_prints_receipt(self):
        """
        TEST 18: Customer prints receipt.
        Expected: Printable HTML receipt rendered with correct order data and print trigger.
        """
        self.client.login(username='customer1@cartivo.com', password='Password@123')
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.phone, quantity=1)
        order = OrderService.create_cod_order(user=self.user, address=self.address)

        response = self.client.get(f"/orders/{order.order_number}/receipt/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CARTIVO')
        self.assertContains(response, 'Official Order Receipt')
        self.assertContains(response, order.order_number)
        self.assertContains(response, 'Cash on Delivery')
        self.assertContains(response, 'window.print()')


class CustomerShippingAndTrackingTests(TestCase):
    """
    Validation test suite for Requirements 49 to 66:
    Customer-Facing Shipping Information, Tracking, Timeline, Friendly Statuses,
    COD Payment Flow, Address Snapshot, Contextual Actions, Cancellation, and Security.
    """
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='alex@cartivo.com',
            email='alex@cartivo.com',
            password='Password@123',
            first_name='Alex',
            last_name='Gupta'
        )
        self.other_user = User.objects.create_user(
            username='stranger@cartivo.com',
            email='stranger@cartivo.com',
            password='Password@123',
            first_name='Bob',
            last_name='Smith'
        )

        self.address = Address.objects.create(
            user=self.user,
            full_name='Alex Gupta',
            phone='9876543210',
            street_address='123 Hazratganj',
            apartment='Flat 4B',
            city='Lucknow',
            state='Uttar Pradesh',
            postal_code='226001',
            country='India',
            address_type='shipping',
            is_default=True
        )

        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.brand = Brand.objects.create(name='BrandX', slug='brandx')
        self.warehouse = Warehouse.objects.create(name='Lucknow Hub', code='WH-LKO', is_primary=True)

        self.product = Product.objects.create(
            title='Wireless Noise Cancelling Headphones',
            slug='wireless-headphones',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('1499.00'),
            sku='HD-WRLS-01',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )
        stk = InventoryService.get_or_create_stock(self.product, self.warehouse)
        stk.on_hand_quantity = 25
        stk.status = 'IN_STOCK'
        stk.save()

    def _create_test_order(self):
        cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        return OrderService.create_cod_order(user=self.user, address=self.address)

    def test_customer_friendly_status_mapping(self):
        """Requirement 52: Technical shipping statuses mapped to customer-friendly labels & sentences."""
        order = self._create_test_order()

        expected_mappings = {
            'READY_TO_PACK': ("Your order is being prepared", "Preparing"),
            'PACKED': ("Your order has been packed", "Packed"),
            'READY_TO_SHIP': ("Your order is ready for dispatch", "Ready for Dispatch"),
            'SHIPPED': ("Your order has been shipped", "Shipped"),
            'OUT_FOR_DELIVERY': ("Your order is out for delivery", "Out for Delivery"),
            'DELIVERED': ("Your order has been delivered", "Delivered"),
            'FAILED': ("Delivery attempt was unsuccessful", "Delivery Failed"),
            'RETURNED': ("Your order has been returned", "Returned"),
            'CONFIRMED': ("Your order has been confirmed", "Confirmed"),
            'CANCELLED': ("Your order has been cancelled", "Cancelled"),
        }

        for status_code, (expected_sentence, expected_label) in expected_mappings.items():
            order.status = status_code
            self.assertEqual(order.customer_friendly_status, expected_sentence)
            self.assertEqual(order.customer_status_label, expected_label)
            # Ensure technical internal uppercase code is never exposed as friendly status
            self.assertNotEqual(order.customer_friendly_status, status_code)

    def test_cod_customer_payment_flow(self):
        """Requirements 53 & 54: Cash on Delivery payment flow transitions."""
        order = self._create_test_order()
        self.assertEqual(order.payment_method, 'COD')

        # 1. Order placed
        order.status = 'CONFIRMED'
        order.payment_status = 'PENDING'
        self.assertEqual(order.customer_payment_display, "Payment Pending")
        self.assertEqual(order.customer_payment_note, "Cash on Delivery — Payment pending")

        # 2. Delivered, but cash collection confirmation pending
        order.status = 'DELIVERED'
        order.payment_status = 'PENDING'
        self.assertEqual(order.customer_payment_display, "Payment Pending")
        self.assertEqual(order.customer_payment_note, "Order delivered. Payment confirmation pending.")

        # 3. Cash collection confirmed by Shipping Department
        order.status = 'DELIVERED'
        order.payment_status = 'PAID'
        self.assertEqual(order.customer_payment_display, "Payment Received")
        self.assertEqual(order.customer_payment_note, "Payment received")

    def test_customer_shipping_timeline(self):
        """Requirement 51: Dynamic timeline generated from actual checkpoints."""
        order = self._create_test_order()

        # Initially CONFIRMED
        timeline = order.customer_timeline
        self.assertEqual(len(timeline), 5)
        self.assertTrue(timeline[0]['completed'])
        self.assertEqual(timeline[0]['title'], 'Order Confirmed')
        self.assertFalse(timeline[1]['completed'])
        self.assertEqual(timeline[1]['display_time'], 'Pending')

        # Add packed checkpoint
        DeliveryCheckpoint.objects.create(
            order=order,
            status='PACKED',
            location='Warehouse Dispatch Bay',
            notes='Packed securely',
            is_customer_visible=True
        )
        order.status = 'PACKED'
        timeline = order.customer_timeline
        self.assertTrue(timeline[0]['completed'])
        self.assertTrue(timeline[1]['completed'])
        self.assertNotEqual(timeline[1]['display_time'], 'Pending')
        self.assertFalse(timeline[2]['completed'])

        # Advance to DELIVERED
        order.status = 'DELIVERED'
        order.delivered_at = timezone.now()
        timeline = order.customer_timeline
        self.assertTrue(timeline[4]['completed'])
        self.assertFalse(timeline[4]['is_pending'])

    def test_delivery_address_snapshot_immutability(self):
        """Requirement 56: Delivery address is an immutable snapshot; changing profile address does not affect old orders."""
        order = self._create_test_order()
        self.assertEqual(order.shipping_city, 'Lucknow')
        self.assertEqual(order.shipping_street_address, '123 Hazratganj')

        # Customer later updates profile address to Bengaluru
        self.address.street_address = '99 Indiranagar'
        self.address.city = 'Bengaluru'
        self.address.state = 'Karnataka'
        self.address.postal_code = '560038'
        self.address.save()

        # Order must still display original Lucknow address
        order.refresh_from_db()
        self.assertEqual(order.shipping_city, 'Lucknow')
        self.assertEqual(order.shipping_street_address, '123 Hazratganj')
        self.assertIn('Lucknow', order.formatted_shipping_address)
        self.assertNotIn('Bengaluru', order.formatted_shipping_address)

        # In template rendering
        self.client.login(username='alex@cartivo.com', password='Password@123')
        res = self.client.get(f"/orders/{order.order_number}/")
        self.assertContains(res, '123 Hazratganj')
        self.assertContains(res, 'Lucknow')
        self.assertNotContains(res, 'Indiranagar')

    def test_customer_data_access_security(self):
        """Requirement 62: Customer can access ONLY their own orders. User B cannot view User A's order."""
        order = self._create_test_order()

        # Stranger attempts to view User A's order detail -> 404
        self.client.login(username='stranger@cartivo.com', password='Password@123')
        res = self.client.get(f"/orders/{order.order_number}/")
        self.assertEqual(res.status_code, 404)

        # Stranger attempts to view User A's receipt -> 404
        res = self.client.get(f"/orders/{order.order_number}/receipt/")
        self.assertEqual(res.status_code, 404)

        # Stranger attempts to cancel User A's order -> 403 Forbidden
        res = self.client.post(f"/orders/{order.order_number}/cancel/")
        self.assertEqual(res.status_code, 403)

    def test_customer_order_cancellation_rules(self):
        """Requirement 61: Order cancellation allowed on CONFIRMED, but restricted on PACKED, SHIPPED, DELIVERED."""
        order = self._create_test_order()
        self.client.login(username='alex@cartivo.com', password='Password@123')

        # When CONFIRMED: Cancellation allowed
        self.assertTrue(order.can_cancel)
        initial_stock = Stock.objects.get(product=self.product, warehouse=self.warehouse).on_hand_quantity
        res = self.client.post(f"/orders/{order.order_number}/cancel/")
        self.assertEqual(res.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, 'CANCELLED')
        # Check stock restored
        new_stock = Stock.objects.get(product=self.product, warehouse=self.warehouse).on_hand_quantity
        self.assertEqual(new_stock, initial_stock + 1)
        # Check checkpoint created
        self.assertTrue(order.checkpoints.filter(status='CANCELLED').exists())

        # Test restriction when order is PACKED or SHIPPED
        order2 = self._create_test_order()
        order2.status = 'SHIPPED'
        order2.save()
        self.assertFalse(order2.can_cancel)

        res = self.client.post(f"/orders/{order2.order_number}/cancel/")
        order2.refresh_from_db()
        self.assertEqual(order2.status, 'SHIPPED')  # Not cancelled!

    def test_contextual_actions_display(self):
        """Requirement 60: Dynamic actions based on order status."""
        order = self._create_test_order()
        self.client.login(username='alex@cartivo.com', password='Password@123')

        # 1. When CONFIRMED
        res = self.client.get(f"/orders/{order.order_number}/")
        self.assertContains(res, "View / Print Receipt")
        self.assertContains(res, "Cancel Order")
        self.assertNotContains(res, "View Payment Receipt")

        # 2. When SHIPPED with tracking URL
        order.status = 'SHIPPED'
        order.tracking_number = 'DLV123456'
        order.tracking_url = 'https://delhivery.com/track/DLV123456'
        order.save()

        res = self.client.get(f"/orders/{order.order_number}/")
        self.assertContains(res, "Track Shipment")
        self.assertContains(res, "https://delhivery.com/track/DLV123456")
        self.assertNotContains(res, "Cancel Order")

        # 3. When DELIVERED and COD payment received (PAID)
        order.status = 'DELIVERED'
        order.payment_status = 'PAID'
        order.save()

        res = self.client.get(f"/orders/{order.order_number}/")
        self.assertContains(res, "View Payment Receipt")

    def test_no_internal_operational_data_leakage(self):
        """Requirement 63: Internal operational data is NEVER exposed to customer."""
        order = self._create_test_order()
        order.cod_collected_by = "EMP-SECRET-884"
        order.cod_received_amount = Decimal('1499.00')
        order.delivery_failure_reason = "INTERNAL_GATE_SECURITY_REJECTED"
        order.internal_notes = "Customer phone was switched off at 4 PM"
        order.save()

        self.client.login(username='alex@cartivo.com', password='Password@123')
        res = self.client.get(f"/orders/{order.order_number}/")
        self.assertNotContains(res, "EMP-SECRET-884")
        self.assertNotContains(res, "INTERNAL_GATE_SECURITY_REJECTED")
        self.assertNotContains(res, "Customer phone was switched off at 4 PM")

        res_receipt = self.client.get(f"/orders/{order.order_number}/receipt/")
        self.assertNotContains(res_receipt, "EMP-SECRET-884")
        self.assertNotContains(res_receipt, "INTERNAL_GATE_SECURITY_REJECTED")

    def test_customer_notifications_dispatch_and_inbox(self):
        """Requirements 58 & 59: Shipping events trigger customer notifications; strictly scoped to order owner."""
        order = self._create_test_order()

        # Trigger shipping notification
        from apps.notifications.services import notify_order_event
        from apps.notifications.models import Notification

        notify_order_event(order, 'ORDER_SHIPPED')
        notify_order_event(order, 'COD_PAYMENT_RECEIVED')

        # Owner has notifications
        self.client.login(username='alex@cartivo.com', password='Password@123')
        res = self.client.get('/notifications/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, f"Your order {order.order_number} has been shipped.")
        self.assertContains(res, f"COD payment of ₹{order.total_amount} has been received.")

        # Stranger has zero notifications
        self.client.login(username='stranger@cartivo.com', password='Password@123')
        res_stranger = self.client.get('/notifications/')
        self.assertNotContains(res_stranger, order.order_number)
        self.assertEqual(Notification.objects.filter(user=self.other_user).count(), 0)

