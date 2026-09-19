from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.accounts.models import Address
from apps.catalog.models import Category, Brand, Product, ProductVariant
from apps.inventory.models import Warehouse, Stock, StockMovement
from apps.inventory.services import InventoryService
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
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
