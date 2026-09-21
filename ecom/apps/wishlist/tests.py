from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.catalog.models import Category, Brand, Product, ProductVariant
from apps.inventory.models import Stock, Warehouse
from apps.cart.models import Cart, CartItem
from apps.cart.services import CartService
from apps.orders.models import Order
from apps.wishlist.models import Wishlist, WishlistItem
from apps.wishlist.services import WishlistService

User = get_user_model()


class WishlistSystemComprehensiveTests(TestCase):
    """
    Comprehensive test suite covering all 20 required business, architectural,
    and security rules for the integrated Wishlist module.
    """

    def setUp(self):
        self.client = Client()

        # Users
        self.customer1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='password123',
            first_name='Alice'
        )
        self.customer2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='password123',
            first_name='Bob'
        )

        # Catalog setup
        self.category = Category.objects.create(name='Smartphones', slug='smartphones')
        self.brand = Brand.objects.create(name='Apple', slug='apple')

        # Product 1: In stock
        self.product1 = Product.objects.create(
            title='iPhone 17 Pro',
            slug='iphone-17-pro',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('999.00'),
            compare_at_price=Decimal('1099.00'),
            sku='IP17P-BASE',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )

        # Product 2: Out of stock
        self.product2 = Product.objects.create(
            title='AirPods Max 2',
            slug='airpods-max-2',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('549.00'),
            sku='APM2-BASE',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )

        # Warehouse and stock
        self.warehouse = Warehouse.objects.create(
            name='Central Depot',
            code='DEPOT-01'
        )
        # 50 units for product 1
        self.stock1 = Stock.objects.create(
            product=self.product1,
            warehouse=self.warehouse,
            on_hand_quantity=50
        )
        # 0 units for product 2
        self.stock2 = Stock.objects.create(
            product=self.product2,
            warehouse=self.warehouse,
            on_hand_quantity=0
        )

    # 1. Authenticated user opens Wishlist
    def test_01_authenticated_user_opens_wishlist(self):
        self.client.login(username='alice', password='password123')
        res = self.client.get(reverse('wishlist:wishlist_view'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'My Wishlist')
        self.assertContains(res, 'Your Wishlist is Empty')

    # 2. User adds product to Wishlist
    def test_02_user_adds_product_to_wishlist(self):
        self.client.login(username='alice', password='password123')
        res = self.client.post(reverse('wishlist:toggle_wishlist'), {
            'product_id': self.product1.id
        })
        self.assertEqual(res.status_code, 302)
        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 1)
        self.assertTrue(wishlist.items.filter(product=self.product1).exists())

    # 3. Same product added again (no duplicate)
    def test_03_no_duplicate_wishlist_items(self):
        # Add once
        item1, created1 = WishlistService.add_to_wishlist(self.customer1, self.product1)
        self.assertTrue(created1)

        # Add again
        item2, created2 = WishlistService.add_to_wishlist(self.customer1, self.product1)
        self.assertFalse(created2)
        self.assertEqual(item1.id, item2.id)

        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 1)

    # 4. User removes product
    def test_04_user_removes_product_from_wishlist(self):
        WishlistService.add_to_wishlist(self.customer1, self.product1)
        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 1)

        removed = WishlistService.remove_from_wishlist(self.customer1, self.product1.id)
        self.assertTrue(removed)
        self.assertEqual(wishlist.items.count(), 0)

    # 5. Wishlist count updates
    def test_05_wishlist_count_updates(self):
        wishlist = WishlistService.get_or_create_wishlist(self.customer1)
        self.assertEqual(wishlist.total_items, 0)

        WishlistService.add_to_wishlist(self.customer1, self.product1)
        self.assertEqual(wishlist.total_items, 1)

        WishlistService.add_to_wishlist(self.customer1, self.product2)
        self.assertEqual(wishlist.total_items, 2)

        WishlistService.remove_from_wishlist(self.customer1, self.product1.id)
        self.assertEqual(wishlist.total_items, 1)

    # 6. Product Detail Wishlist button updates
    def test_06_product_detail_shows_wishlist_state(self):
        self.client.login(username='alice', password='password123')

        # Initially not in wishlist
        res = self.client.get(self.product1.get_absolute_url())
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.context['is_in_wishlist'])
        self.assertContains(res, 'Add to Wishlist')

        # Add to wishlist
        WishlistService.add_to_wishlist(self.customer1, self.product1)

        # Now in wishlist
        res = self.client.get(self.product1.get_absolute_url())
        self.assertTrue(res.context['is_in_wishlist'])
        self.assertContains(res, 'Remove from Wishlist')

    # 7. Product Card Wishlist button updates
    def test_07_product_card_wishlist_context(self):
        self.client.login(username='alice', password='password123')
        WishlistService.add_to_wishlist(self.customer1, self.product1)

        res = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(res.status_code, 200)
        self.assertIn(self.product1.id, res.context['user_wishlist_product_ids'])
        self.assertNotIn(self.product2.id, res.context['user_wishlist_product_ids'])

    # 8. Wishlist item is added to Cart (existing Cart is used)
    def test_08_wishlist_item_added_to_cart(self):
        self.client.login(username='alice', password='password123')
        item, _ = WishlistService.add_to_wishlist(self.customer1, self.product1)

        res = self.client.post(reverse('wishlist:add_to_cart', kwargs={'item_id': item.id}))
        self.assertEqual(res.status_code, 302)

        cart = Cart.objects.get(user=self.customer1, status='ACTIVE')
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().product, self.product1)

        # Still in wishlist!
        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 1)

    # 9. Wishlist item is moved to Cart (Cart updated + Wishlist item removed)
    def test_09_wishlist_item_moved_to_cart(self):
        self.client.login(username='alice', password='password123')
        item, _ = WishlistService.add_to_wishlist(self.customer1, self.product1)

        res = self.client.post(reverse('wishlist:move_to_cart', kwargs={'item_id': item.id}))
        self.assertEqual(res.status_code, 302)

        # Cart updated
        cart = Cart.objects.get(user=self.customer1, status='ACTIVE')
        self.assertEqual(cart.items.count(), 1)

        # Removed from wishlist!
        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 0)

    # 10. Out-of-stock item remains in Wishlist
    def test_10_out_of_stock_item_remains_in_wishlist(self):
        item, _ = WishlistService.add_to_wishlist(self.customer1, self.product2)
        self.assertFalse(item.is_in_stock)
        self.assertEqual(item.stock_status_label, 'Out of Stock')

        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 1)

        self.client.login(username='alice', password='password123')
        res = self.client.get(reverse('wishlist:wishlist_view'))
        self.assertContains(res, 'Out of Stock')
        self.assertContains(res, 'AirPods Max 2')

    # 11. Out-of-stock item cannot be added to Cart
    def test_11_out_of_stock_item_cannot_be_added_to_cart(self):
        self.client.login(username='alice', password='password123')
        item, _ = WishlistService.add_to_wishlist(self.customer1, self.product2)

        # Attempt to move to cart
        res = self.client.post(reverse('wishlist:move_to_cart', kwargs={'item_id': item.id}))
        self.assertEqual(res.status_code, 302)

        # Cart must remain empty
        cart = Cart.objects.filter(user=self.customer1, status='ACTIVE').first()
        self.assertTrue(cart is None or cart.items.count() == 0)

        # Item must NOT be removed from wishlist
        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertEqual(wishlist.items.count(), 1)

    # 12. Guest clicks Add to Wishlist redirects to login with ?next=
    def test_12_guest_redirected_to_login(self):
        res = self.client.post(reverse('wishlist:toggle_wishlist'), {
            'product_id': self.product1.id
        })
        self.assertEqual(res.status_code, 302)
        self.assertIn('/accounts/login/', res.url)
        self.assertIn('next=', res.url)

    # 13. Guest AJAX request receives 401 with login_url
    def test_13_guest_ajax_receives_401(self):
        res = self.client.post(
            reverse('wishlist:toggle_wishlist'),
            data={'product_id': self.product1.id},
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(res.status_code, 401)
        data = res.json()
        self.assertTrue(data['login_required'])
        self.assertIn('/accounts/login/', data['login_url'])

    # 14. Customer A cannot access Customer B's Wishlist
    def test_14_customer_isolation(self):
        # Alice saves product 1
        item_alice, _ = WishlistService.add_to_wishlist(self.customer1, self.product1)

        # Bob logs in and tries to remove Alice's wishlist item
        self.client.login(username='bob', password='password123')
        res = self.client.post(reverse('wishlist:remove_item', kwargs={'item_id': item_alice.id}))
        self.assertEqual(res.status_code, 302)

        # Alice's item is NOT deleted
        self.assertTrue(WishlistItem.objects.filter(id=item_alice.id).exists())

        # Bob views his wishlist - does not see Alice's product
        res = self.client.get(reverse('wishlist:wishlist_view'))
        self.assertNotContains(res, 'iPhone 17 Pro')

    # 15. Product price changes in Catalog -> Wishlist shows current price
    def test_15_wishlist_reflects_current_catalog_price(self):
        item, _ = WishlistService.add_to_wishlist(self.customer1, self.product1)
        self.assertEqual(item.effective_price, Decimal('999.00'))

        # Change price in catalog
        self.product1.base_price = Decimal('849.00')
        self.product1.save()

        # WishlistItem reads live price without saving anything
        item.refresh_from_db()
        self.assertEqual(item.effective_price, Decimal('849.00'))

    # 16. Product becomes unavailable -> Wishlist remains safe
    def test_16_product_becomes_unavailable(self):
        item, _ = WishlistService.add_to_wishlist(self.customer1, self.product1)
        self.assertTrue(item.is_in_stock)

        # Soft-disable product
        self.product1.status = 'DRAFT'
        self.product1.save()

        item.refresh_from_db()
        self.assertFalse(item.is_in_stock)
        self.assertEqual(item.stock_status_label, 'Unavailable')

    # 17. Wishlist does not modify inventory
    def test_17_wishlist_does_not_modify_inventory(self):
        initial_stock = self.stock1.on_hand_quantity

        # Add to wishlist
        WishlistService.add_to_wishlist(self.customer1, self.product1)
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.on_hand_quantity, initial_stock)

        # Toggle out of wishlist
        WishlistService.toggle_wishlist(self.customer1, self.product1)
        self.stock1.refresh_from_db()
        self.assertEqual(self.stock1.on_hand_quantity, initial_stock)

    # 18. Wishlist does not create Orders
    def test_18_wishlist_does_not_create_orders(self):
        initial_orders = Order.objects.count()

        WishlistService.add_to_wishlist(self.customer1, self.product1)
        WishlistService.add_to_wishlist(self.customer1, self.product2)

        self.assertEqual(Order.objects.count(), initial_orders)

    # 19. Add All to Cart only adds in-stock items
    def test_19_add_all_to_cart_only_in_stock(self):
        # Alice has product 1 (in stock) and product 2 (out of stock)
        WishlistService.add_to_wishlist(self.customer1, self.product1)
        WishlistService.add_to_wishlist(self.customer1, self.product2)

        self.client.login(username='alice', password='password123')
        res = self.client.post(reverse('wishlist:add_all_to_cart'), follow=True)
        self.assertEqual(res.status_code, 200)

        # Cart should contain ONLY product 1
        cart = Cart.objects.get(user=self.customer1, status='ACTIVE')
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().product, self.product1)

        # Wishlist still has product 2 (out of stock)
        wishlist = Wishlist.get_default_for_user(self.customer1)
        self.assertTrue(wishlist.items.filter(product=self.product2).exists())

    # 20. Navbar Wishlist count is correct via context processor
    def test_20_navbar_wishlist_count_in_context(self):
        # Anonymous user
        res = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(res.context['wishlist_item_count'], 0)

        # Authenticated user with items
        WishlistService.add_to_wishlist(self.customer1, self.product1)
        WishlistService.add_to_wishlist(self.customer1, self.product2)

        self.client.login(username='alice', password='password123')
        res = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(res.context['wishlist_item_count'], 2)
