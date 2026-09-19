from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.orders.models import Order, OrderItem
from apps.catalog.models import Product, Category, ProductVariant
from apps.inventory.models import Warehouse, Stock
from apps.cart.models import Cart
from apps.core.services.dashboard_metrics import get_superadmin_dashboard_metrics, format_currency_inr

User = get_user_model()


class SuperadminDashboardMetricsTests(TestCase):
    """
    Automated integration tests for multi-app business intelligence metrics
    (sales, profit, COGS, profit margin, category breakdown, inventory valuation, cart conversion).
    """

    def setUp(self):
        self.client = Client()
        
        # 1. Superuser & Normal User
        self.superuser = User.objects.create_superuser(
            username='admin_boss',
            email='admin@cartivo.local',
            password='Password123!'
        )
        self.customer = User.objects.create_user(
            username='customer_jane',
            email='jane@customer.local',
            password='Password123!'
        )

        # 2. Categories
        self.cat_apparel = Category.objects.create(name='Apparel & Fashion', slug='apparel-fashion')
        self.cat_tech = Category.objects.create(name='Tech Gadgets', slug='tech-gadgets')

        # 3. Products & Variants with Cost Prices
        # Product 1: Jacket (Selling: 5000, Cost: 2500)
        self.prod_jacket = Product.objects.create(
            title='Artisan Wool Jacket',
            slug='artisan-wool-jacket',
            category=self.cat_apparel,
            base_price=Decimal('5000.00'),
            cost_price=Decimal('2500.00'),
            sku='JKT-001',
            status='ACTIVE'
        )
        # Product 2: Drone (Selling: 10000, Cost: 6000)
        self.prod_drone = Product.objects.create(
            title='AeroX Stealth Drone',
            slug='aerox-stealth-drone',
            category=self.cat_tech,
            base_price=Decimal('10000.00'),
            cost_price=Decimal('6000.00'),
            sku='DRN-001',
            status='ACTIVE'
        )
        self.drone_var = ProductVariant.objects.create(
            product=self.prod_drone,
            sku='DRN-001-PRO',
            name='Pro Edition',
            price=Decimal('12000.00'),
            cost_price=Decimal('7000.00'),
            is_active=True
        )

        # 4. Inventory Warehouse & Stock
        self.warehouse = Warehouse.objects.create(
            name='Hub One',
            code='HUB-01',
            is_primary=True,
            status='ACTIVE'
        )
        self.stock_jacket = Stock.objects.create(
            product=self.prod_jacket,
            warehouse=self.warehouse,
            on_hand_quantity=50,
            status='IN_STOCK'
        )
        self.stock_drone = Stock.objects.create(
            product=self.prod_drone,
            variant=self.drone_var,
            warehouse=self.warehouse,
            on_hand_quantity=20,
            status='IN_STOCK'
        )

        # 5. Carts (1 converted, 1 active)
        self.cart_converted = Cart.objects.create(user=self.customer, status='CONVERTED')
        self.cart_active = Cart.objects.create(user=self.customer, status='ACTIVE')

        # 6. Orders
        # Order 1: Delivered, Total: 17000 (1 Jacket @ 5000, 1 Drone Pro @ 12000)
        # Cost: 2500 + 7000 = 9500. Profit: 17000 - 9500 = 7500.
        self.order_1 = Order.objects.create(
            order_number='ORD-TEST-001',
            user=self.customer,
            status='DELIVERED',
            payment_method='COD',
            payment_status='PAID',
            subtotal=Decimal('17000.00'),
            total_amount=Decimal('17000.00'),
            discount_amount=Decimal('0.00')
        )
        OrderItem.objects.create(
            order=self.order_1,
            product=self.prod_jacket,
            sku='JKT-001',
            product_title=self.prod_jacket.title,
            unit_price=Decimal('5000.00'),
            quantity=1,
            subtotal=Decimal('5000.00')
        )
        OrderItem.objects.create(
            order=self.order_1,
            product=self.prod_drone,
            variant=self.drone_var,
            sku='DRN-001-PRO',
            product_title=self.prod_drone.title,
            variant_name='Pro Edition',
            unit_price=Decimal('12000.00'),
            quantity=1,
            subtotal=Decimal('12000.00')
        )

        # Order 2: Confirmed, Total: 10000 (2 Jackets @ 5000)
        # Cost: 2 * 2500 = 5000. Profit: 10000 - 5000 = 5000.
        self.order_2 = Order.objects.create(
            order_number='ORD-TEST-002',
            user=self.customer,
            status='CONFIRMED',
            payment_method='COD',
            payment_status='PENDING',
            subtotal=Decimal('10000.00'),
            total_amount=Decimal('10000.00'),
            discount_amount=Decimal('0.00')
        )
        OrderItem.objects.create(
            order=self.order_2,
            product=self.prod_jacket,
            sku='JKT-001',
            product_title=self.prod_jacket.title,
            unit_price=Decimal('5000.00'),
            quantity=2,
            subtotal=Decimal('10000.00')
        )

        # Order 3: Cancelled (should be excluded from revenue & profit calculations)
        self.order_cancelled = Order.objects.create(
            order_number='ORD-TEST-CANCELLED',
            user=self.customer,
            status='CANCELLED',
            payment_method='COD',
            payment_status='FAILED',
            subtotal=Decimal('5000.00'),
            total_amount=Decimal('5000.00'),
            discount_amount=Decimal('0.00')
        )

    def test_metrics_engine_sales_and_profit_calculation(self):
        """Verify get_superadmin_dashboard_metrics correctly calculates revenue, COGS, profit, and margin."""
        metrics = get_superadmin_dashboard_metrics()

        # Gross Revenue = 17000 + 10000 = 27000 (Order 3 Cancelled excluded)
        self.assertEqual(metrics['gross_revenue'], Decimal('27000.00'))
        
        # Total COGS:
        # Order 1: Jacket (2500) + Drone Pro (7000) = 9500
        # Order 2: 2 Jackets (2 * 2500 = 5000)
        # Total COGS = 9500 + 5000 = 14500
        self.assertEqual(metrics['total_cogs'], Decimal('14500.00'))

        # Gross Profit = 27000 - 14500 = 12500
        self.assertEqual(metrics['gross_profit'], Decimal('12500.00'))

        # Profit Margin = (12500 / 27000) * 100 = ~46.296% -> 46.3%
        self.assertAlmostEqual(metrics['profit_margin_pct'], 46.3, delta=0.1)

        # Order counts
        self.assertEqual(metrics['total_orders_count'], 3)
        self.assertEqual(metrics['completed_orders_count'], 1)
        self.assertEqual(metrics['pending_orders_count'], 1)
        self.assertEqual(metrics['cancelled_orders_count'], 1)

        # Units sold: 1 + 1 + 2 = 4 units
        self.assertEqual(metrics['total_units_sold'], 4)

        # Average Order Value (AOV): 27000 / 3 = 9000
        self.assertEqual(metrics['aov'], Decimal('9000.00'))

    def test_metrics_engine_inventory_and_cart_conversion(self):
        """Verify inventory valuation and cart funnel conversion calculations."""
        metrics = get_superadmin_dashboard_metrics()

        # Stock jacket: 50 on hand * 2500 cost = 125,000
        # Stock drone pro: 20 on hand * 7000 cost = 140,000
        # Total inventory valuation = 265,000
        self.assertEqual(metrics['inventory_valuation'], Decimal('265000.00'))
        self.assertEqual(metrics['total_units_on_hand'], 70)
        self.assertEqual(metrics['warehouse_count'], 1)

        # Carts: 2 total, 1 active, 1 converted -> 50.0% conversion
        self.assertEqual(metrics['total_carts'], 2)
        self.assertEqual(metrics['active_carts'], 1)
        self.assertEqual(metrics['converted_carts'], 1)
        self.assertEqual(metrics['cart_conversion_rate'], 50.0)

    def test_metrics_engine_category_and_top_products(self):
        """Verify category breakdown and top performing products ranking."""
        metrics = get_superadmin_dashboard_metrics()

        # Category sales:
        # Apparel: 5000 + 10000 = 15000
        # Tech: 12000
        cat_names = [c['name'] for c in metrics['category_breakdown']]
        self.assertIn('Apparel & Fashion', cat_names)
        self.assertIn('Tech Gadgets', cat_names)

        # Top products
        top_titles = [p['title'] for p in metrics['top_products']]
        self.assertIn('Artisan Wool Jacket', top_titles)
        self.assertIn('AeroX Stealth Drone', top_titles)

    def test_superadmin_dashboard_view_access_and_rendering(self):
        """Verify superadmin_dashboard_view renders HTTP 200 with live context for superuser."""
        # Unauthenticated redirects to login
        response = self.client.get(reverse('management:dashboard'))
        self.assertEqual(response.status_code, 302)

        # Authenticate as superuser
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('management:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Verify context variables
        self.assertIn('gross_revenue', response.context)
        self.assertIn('gross_profit', response.context)
        self.assertIn('profit_margin_pct', response.context)
        self.assertIn('inventory_valuation_display', response.context)
        self.assertIn('cart_conversion_rate_display', response.context)
        self.assertIn('top_products', response.context)
        self.assertIn('category_breakdown', response.context)
        self.assertIn('recent_orders', response.context)

        # Content verification in HTML
        content = response.content.decode('utf-8')
        self.assertIn('Executive Net Performance', content)
        self.assertIn('Category Sales Breakdown', content)
        self.assertIn('Top Performing Products', content)
        self.assertIn('Warehouse Network', content)

    def test_superadmin_sales_view_access_and_rendering(self):
        """Verify superadmin_sales_view renders HTTP 200 with live context for superuser."""
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('management:sales'))
        self.assertEqual(response.status_code, 200)

        self.assertIn('gross_revenue', response.context)
        self.assertIn('gross_profit', response.context)
        self.assertIn('aov_val', response.context)
        self.assertIn('recent_orders', response.context)

        content = response.content.decode('utf-8')
        self.assertIn('Gross Revenue', content)
        self.assertIn('Recent Platform Sales &amp; Orders Ledger', content)
