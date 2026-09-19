from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.catalog.models import Category, Brand, Product, ProductVariant
from apps.inventory.models import Warehouse, Stock
from apps.inventory.services import InventoryService
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService


class CartFlowIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            password='Password@123'
        )
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.brand = Brand.objects.create(name='Cartivo Tech', slug='cartivo-tech')
        self.warehouse = Warehouse.objects.create(name='Central Hub', code='WH-CENTRAL', is_primary=True)

        # Standard standalone product
        self.product = Product.objects.create(
            title='Wireless Noise-Canceling Headphones',
            slug='wireless-headphones',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('150.00'),
            sku='TECH-HP-001',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )
        # Stock: 10 units
        self.stock = InventoryService.get_or_create_stock(self.product, self.warehouse)
        self.stock.on_hand_quantity = 10
        self.stock.status = 'IN_STOCK'
        self.stock.save()

        # Variable product with 2 variants
        self.var_product = Product.objects.create(
            title='Premium Cotton T-Shirt',
            slug='premium-cotton-t-shirt',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('40.00'),
            product_type='variable',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )
        self.variant_black = ProductVariant.objects.create(
            product=self.var_product,
            sku='TSHIRT-BLK-L',
            name='Black / L',
            price=Decimal('45.00')
        )
        self.variant_white = ProductVariant.objects.create(
            product=self.var_product,
            sku='TSHIRT-WHT-M',
            name='White / M',
            price=Decimal('40.00')
        )
        # Stock for variants
        stk_blk = InventoryService.get_or_create_stock(self.var_product, self.warehouse, variant=self.variant_black)
        stk_blk.on_hand_quantity = 5
        stk_blk.status = 'IN_STOCK'
        stk_blk.save()

        stk_wht = InventoryService.get_or_create_stock(self.var_product, self.warehouse, variant=self.variant_white)
        stk_wht.on_hand_quantity = 8
        stk_wht.status = 'IN_STOCK'
        stk_wht.save()

    def test_01_guest_can_browse_product(self):
        """TEST 1: Guest opens product."""
        response = self.client.get(f"/products/{self.product.slug}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.title)

    def test_02_guest_adds_product_to_cart(self):
        """TEST 2: Guest adds product to cart without login."""
        response = self.client.post('/cart/add/', {
            'product_id': self.product.id,
            'quantity': 2,
        })
        self.assertEqual(response.status_code, 302)  # Redirects to cart
        self.assertIn('guest_cart', self.client.session)
        key = f"{self.product.id}_0"
        self.assertEqual(self.client.session['guest_cart'][key]['quantity'], 2)

    def test_03_guest_views_cart(self):
        """TEST 3: Guest views cart."""
        self.client.post('/cart/add/', {'product_id': self.product.id, 'quantity': 1})
        response = self.client.get('/cart/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.title)
        self.assertContains(response, 'Shopping Bag')

    def test_04_guest_updates_quantity(self):
        """TEST 4: Guest updates quantity."""
        self.client.post('/cart/add/', {'product_id': self.product.id, 'quantity': 1})
        key = f"{self.product.id}_0"
        response = self.client.post('/cart/update/', {
            'item_key': key,
            'quantity': 3,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['guest_cart'][key]['quantity'], 3)

    def test_05_guest_removes_product(self):
        """TEST 5: Guest removes product."""
        self.client.post('/cart/add/', {'product_id': self.product.id, 'quantity': 1})
        key = f"{self.product.id}_0"
        response = self.client.post('/cart/remove/', {'item_key': key})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(key, self.client.session['guest_cart'])

    def test_06_guest_adds_multiple_variants(self):
        """TEST 6: Guest adds multiple variants."""
        self.client.post('/cart/add/', {
            'product_id': self.var_product.id,
            'variant_id': self.variant_black.id,
            'quantity': 2,
        })
        self.client.post('/cart/add/', {
            'product_id': self.var_product.id,
            'variant_id': self.variant_white.id,
            'quantity': 1,
        })
        key_blk = f"{self.var_product.id}_{self.variant_black.id}"
        key_wht = f"{self.var_product.id}_{self.variant_white.id}"
        self.assertEqual(self.client.session['guest_cart'][key_blk]['quantity'], 2)
        self.assertEqual(self.client.session['guest_cart'][key_wht]['quantity'], 1)

    def test_07_guest_proceeds_to_checkout_redirects_to_login(self):
        """TEST 7: Guest proceeds to checkout. Expected: redirect to login."""
        response = self.client.get('/checkout/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/accounts/login/' in response.url)

    def test_08_guest_cart_merges_on_login(self):
        """TEST 8: Guest logs in -> Guest cart merges into customer DB cart."""
        # Guest puts item in cart
        self.client.post('/cart/add/', {'product_id': self.product.id, 'quantity': 2})
        self.client.post('/cart/add/', {
            'product_id': self.var_product.id,
            'variant_id': self.variant_black.id,
            'quantity': 1,
        })

        # Login
        login_res = self.client.post('/accounts/login/', {
            'email': 'buyer@example.com',
            'password': 'Password@123',
            'next': '/checkout/'
        })
        self.assertEqual(login_res.status_code, 302)

        # User's DB cart should have both items
        user_cart = Cart.objects.filter(user=self.user, status='ACTIVE').first()
        self.assertIsNotNone(user_cart)
        self.assertEqual(user_cart.items.count(), 2)

        # Session cart should be cleared
        self.assertEqual(self.client.session.get('guest_cart', {}), {})

    def test_09_existing_user_cart_plus_guest_cart_same_sku_merge_quantities(self):
        """TEST 9: Existing user cart + guest cart with same SKU -> Quantities merge correctly."""
        # User already has 1 headphones in DB cart
        user_cart = Cart.objects.create(user=self.user, status='ACTIVE')
        CartItem.objects.create(cart=user_cart, product=self.product, quantity=1)

        # Guest adds 2 headphones in session
        self.client.post('/cart/add/', {'product_id': self.product.id, 'quantity': 2})

        # Login
        self.client.post('/accounts/login/', {
            'email': 'buyer@example.com',
            'password': 'Password@123',
        })

        # DB cart should now have 1 + 2 = 3 headphones
        user_cart.refresh_from_db()
        item = user_cart.items.get(product=self.product)
        self.assertEqual(item.quantity, 3)
