from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.catalog.models import Category, Brand, Product, ProductVariant
from apps.inventory.models import Stock, Warehouse
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review, ReviewReply, ReviewVote, ReviewMedia
from apps.reviews.services import ReviewService

User = get_user_model()


class ReviewSystemComprehensiveTests(TestCase):
    """
    Comprehensive test suite covering all 24 required business and architectural rules
    for the integrated Reviews module.
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
        self.staff_admin = User.objects.create_superuser(
            username='admin_staff',
            email='admin@cartivo.com',
            password='password123',
            first_name='Admin'
        )

        # Catalog setup
        self.category = Category.objects.create(name='Smartphones', slug='smartphones')
        self.brand = Brand.objects.create(name='Apple', slug='apple')
        self.product = Product.objects.create(
            title='iPhone 17 Pro',
            slug='iphone-17-pro',
            category=self.category,
            brand=self.brand,
            base_price=Decimal('999.00'),
            sku='IP17P-BASE',
            status='ACTIVE',
            visibility='PUBLIC',
            is_active=True
        )

        # Warehouse and stock
        self.warehouse = Warehouse.objects.create(
            name='Central Depot',
            code='DEPOT-01'
        )
        self.stock = Stock.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            on_hand_quantity=50
        )

    # TEST 1: Authenticated customer opens product
    def test_01_customer_opens_product_detail_sees_reviews_context(self):
        self.client.login(username='alice', password='password123')
        response = self.client.get(self.product.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn('reviews', response.context)
        self.assertIn('review_summary', response.context)
        self.assertContains(response, 'Customer Reviews')
        self.assertContains(response, 'Write a Review')

    # TEST 2 & TEST 3: Customer submits review and it appears on Product Detail
    def test_02_03_customer_submits_review_and_appears_on_page(self):
        self.client.login(username='alice', password='password123')
        url = reverse('reviews:submit_review', kwargs={'slug': self.product.slug})
        response = self.client.post(url, {
            'rating': 5,
            'title': 'Stunning build and camera!',
            'comment': 'I love the new iPhone 17. The titanium finish and battery life are phenomenal.'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        review = Review.objects.get(product=self.product, user=self.customer1)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.title, 'Stunning build and camera!')
        self.assertEqual(review.status, Review.STATUS_APPROVED)

        # Appears on Product Detail
        detail_res = self.client.get(self.product.get_absolute_url())
        self.assertContains(detail_res, 'Stunning build and camera!')
        self.assertContains(detail_res, 'Alice')

    # TEST 4 & TEST 5: Rating summary and review count update
    def test_04_05_rating_summary_and_review_count_updates(self):
        # Alice gives 5 stars
        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Great',
            comment='5 star review'
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.review_count, 1)
        self.assertEqual(self.product.rating, Decimal('5.00'))

        # Bob gives 3 stars
        ReviewService.submit_or_update_review(
            user=self.customer2,
            product=self.product,
            rating=3,
            title='Average',
            comment='3 star review'
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.review_count, 2)
        self.assertEqual(self.product.rating, Decimal('4.00'))  # (5 + 3) / 2 = 4.00

        summary = ReviewService.get_product_review_summary(self.product)
        self.assertEqual(summary['total_reviews'], 2)
        self.assertEqual(summary['average_rating'], 4.0)

    # TEST 6: Customer can see Verified Purchase when eligible (delivered order)
    def test_06_verified_purchase_when_delivered(self):
        # Create delivered order for Alice
        order = Order.objects.create(
            user=self.customer1,
            order_number=Order.generate_order_number(),
            shipping_name='Alice Smith',
            shipping_street_address='123 Luxury Ave',
            shipping_city='Metropolis',
            shipping_state='NY',
            shipping_postal_code='10001',
            status='DELIVERED'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            sku='IP17P-BASE',
            product_title='iPhone 17 Pro',
            unit_price=Decimal('999.00'),
            quantity=1,
            subtotal=Decimal('999.00')
        )

        review, _ = ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Verified review',
            comment='Purchased and received my phone!'
        )
        self.assertTrue(review.is_verified_purchase)

        # Check Product Detail page contains verified badge
        self.client.login(username='alice', password='password123')
        res = self.client.get(self.product.get_absolute_url())
        self.assertContains(res, 'Verified Purchase')

    # TEST 7: Customer cannot fake Verified Purchase from client
    def test_07_customer_cannot_fake_verified_purchase(self):
        self.client.login(username='bob', password='password123')
        url = reverse('reviews:submit_review', kwargs={'slug': self.product.slug})
        # Try sending is_verified_purchase=1 in POST payload
        self.client.post(url, {
            'rating': 4,
            'title': 'Fake verified attempt',
            'comment': 'I never bought this but trying to claim verified.',
            'is_verified_purchase': True
        })
        review = Review.objects.get(product=self.product, user=self.customer2)
        # Must be False because server checks orders directly
        self.assertFalse(review.is_verified_purchase)

    # TEST 8, 9, 10: Admin approves / rejects review; approved is public, rejected is hidden
    def test_08_09_10_moderation_approved_vs_rejected(self):
        review, _ = ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=1,
            title='Inappropriate content',
            comment='Offensive text...'
        )
        # Moderate to REJECTED
        ReviewService.moderate_review(self.staff_admin, review.id, Review.STATUS_REJECTED)
        review.refresh_from_db()
        self.assertEqual(review.status, Review.STATUS_REJECTED)

        # Rejected review must not appear on product detail page
        anonymous_client = Client()
        res = anonymous_client.get(self.product.get_absolute_url())
        self.assertNotContains(res, 'Inappropriate content')

        # Approve review
        ReviewService.moderate_review(self.staff_admin, review.id, Review.STATUS_APPROVED)
        res = anonymous_client.get(self.product.get_absolute_url())
        self.assertContains(res, 'Inappropriate content')

    # TEST 11 & 12: Admin replies to review, reply appears on Product Detail
    def test_11_12_admin_official_reply_appears_on_product_detail(self):
        review, _ = ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Great service',
            comment='Fast delivery and great phone.'
        )

        reply = ReviewService.add_official_reply(
            staff_user=self.staff_admin,
            review_id=review.id,
            reply_text='Thank you Alice, we are delighted you love the iPhone 17!'
        )
        self.assertEqual(reply.review, review)
        self.assertEqual(reply.user, self.staff_admin)

        # Verify reply appears on product detail page
        res = self.client.get(self.product.get_absolute_url())
        self.assertContains(res, 'Thank you Alice, we are delighted you love the iPhone 17!')
        self.assertContains(res, 'Official')

    # TEST 13: Customer cannot create duplicate review for same product
    def test_13_one_review_per_customer_rule(self):
        # First submission
        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=4,
            title='First review',
            comment='First comment'
        )
        self.assertEqual(Review.objects.filter(product=self.product, user=self.customer1).count(), 1)

        # Second submission should update the existing review, not create a duplicate
        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Updated review',
            comment='Updated comment'
        )
        self.assertEqual(Review.objects.filter(product=self.product, user=self.customer1).count(), 1)
        rev = Review.objects.get(product=self.product, user=self.customer1)
        self.assertEqual(rev.rating, 5)
        self.assertEqual(rev.title, 'Updated review')

    # TEST 14 & 15: Customer edits own review, cannot edit another user's review
    def test_14_15_review_editing_permissions(self):
        review, _ = ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=4,
            title='Alice Original',
            comment='Original text'
        )

        # Bob tries to edit Alice's review
        self.client.login(username='bob', password='password123')
        url = reverse('reviews:edit_review', kwargs={'review_id': review.id})
        response = self.client.post(url, {
            'rating': 1,
            'title': 'Hacked',
            'comment': 'Hacked text'
        })
        self.assertEqual(response.status_code, 403)
        review.refresh_from_db()
        self.assertEqual(review.title, 'Alice Original')

        # Alice edits her own review
        self.client.login(username='alice', password='password123')
        response = self.client.post(url, {
            'rating': 5,
            'title': 'Alice Updated',
            'comment': 'Legitimate update'
        })
        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.title, 'Alice Updated')
        self.assertEqual(review.rating, 5)

    # TEST 16: Customer deletes own review, product rating recalculates
    def test_16_customer_deletes_own_review_recalculates_rating(self):
        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='To be deleted',
            comment='Goodbye'
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.review_count, 1)

        self.client.login(username='alice', password='password123')
        review = Review.objects.get(product=self.product, user=self.customer1)
        url = reverse('reviews:delete_review', kwargs={'review_id': review.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        self.assertFalse(Review.objects.filter(id=review.id).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.review_count, 0)

    # TEST 17: Out of stock product can still have and display reviews
    def test_17_out_of_stock_product_reviews(self):
        # Set stock to 0
        self.stock.on_hand_quantity = 0
        self.stock.save()
        self.assertFalse(self.product.is_in_stock)

        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Loved it when in stock',
            comment='Hope it restocks soon!'
        )

        res = self.client.get(self.product.get_absolute_url())
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Loved it when in stock')
        self.assertContains(res, 'Out of Stock')

    # TEST 18, 19, 20: Review does not modify inventory, cart, or orders
    def test_18_19_20_review_does_not_modify_inventory_cart_orders(self):
        initial_stock = self.stock.on_hand_quantity
        cart = Cart.objects.create(user=self.customer1)
        orders_count = Order.objects.count()

        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Safe operation',
            comment='Reviewing should not affect commercial state.'
        )

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.on_hand_quantity, initial_stock)  # Stock untouched
        self.assertEqual(cart.items.count(), 0)               # Cart untouched
        self.assertEqual(Order.objects.count(), orders_count) # No rogue orders

    # TEST 21: Delivered order shows "Review Product"
    def test_21_delivered_order_shows_review_product(self):
        order = Order.objects.create(
            user=self.customer1,
            order_number=Order.generate_order_number(),
            shipping_name='Alice Smith',
            shipping_street_address='123 Main St',
            shipping_city='City',
            shipping_state='State',
            shipping_postal_code='00000',
            status='DELIVERED'
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            sku='IP17P-BASE',
            product_title='iPhone 17 Pro',
            unit_price=Decimal('999.00'),
            quantity=1,
            subtotal=Decimal('999.00')
        )

        self.client.login(username='alice', password='password123')
        res = self.client.get(reverse('orders:order_detail', kwargs={'order_number': order.order_number}))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Review Product')

    # TEST 22: Customer opens My Reviews and sees only their reviews
    def test_22_my_reviews_shows_only_customer_reviews(self):
        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title="Alice exclusive review",
            comment="Alice review content"
        )
        ReviewService.submit_or_update_review(
            user=self.customer2,
            product=self.product,
            rating=2,
            title="Bob review",
            comment="Bob review content"
        )

        self.client.login(username='alice', password='password123')
        res = self.client.get(reverse('reviews:my_reviews'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Alice exclusive review")
        self.assertNotContains(res, "Bob review")

    # TEST 23: Product card rating matches Product Detail rating
    def test_23_product_card_rating_matches_detail(self):
        ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=4,
            title='Good phone',
            comment='Solid 4 stars'
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.rating, Decimal('4.00'))

        # Check Catalog storefront list
        res = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, '4.0')
        self.assertContains(res, '1 review')

    # TEST 24: No reviews shows proper empty state
    def test_24_no_reviews_shows_proper_empty_state(self):
        res = self.client.get(self.product.get_absolute_url())
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'No reviews yet')
        self.assertContains(res, 'Be the first to review')

    # BONUS: Helpful voting toggle
    def test_25_helpful_voting_and_duplicate_prevention(self):
        review, _ = ReviewService.submit_or_update_review(
            user=self.customer1,
            product=self.product,
            rating=5,
            title='Helpful review',
            comment='Very informative text.'
        )
        # Customer 2 votes helpful
        voted, count = ReviewService.vote_helpful(self.customer2, review.id)
        self.assertTrue(voted)
        self.assertEqual(count, 1)

        # Customer 2 votes again (toggles vote off)
        voted, count = ReviewService.vote_helpful(self.customer2, review.id)
        self.assertFalse(voted)
        self.assertEqual(count, 0)
