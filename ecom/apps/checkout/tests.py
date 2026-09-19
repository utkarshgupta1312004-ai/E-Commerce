from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from apps.accounts.models import Address
from apps.catalog.models import Category, Product
from apps.cart.models import Cart, CartItem
from apps.orders.models import Order, DeliveryCheckpoint
from apps.orders.services import OrderService
from apps.core.models import ManagementDepartment, DepartmentAccount

User = get_user_model()


class CheckoutDashboardAndDeliveryTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Customer User
        self.customer = User.objects.create_user(
            username='buyer@cartivo.com',
            email='buyer@cartivo.com',
            password='Password@123'
        )

        # Shipping Address
        self.address = Address.objects.create(
            user=self.customer,
            full_name='Aarav Sharma',
            phone='+91 9876543210',
            street_address='42 Commercial Street',
            city='Bengaluru',
            state='Karnataka',
            postal_code='560001',
            country='India',
            address_type='shipping',
            is_default=True
        )

        # Department & Account for Checkout (CHK001)
        self.dept, _ = ManagementDepartment.objects.get_or_create(
            slug='checkout',
            defaults={'name': 'Checkout Management', 'description': 'Checkout & Logistics'}
        )
        self.chk_user = User.objects.create_user(
            username='CHK001',
            email='chk001@cartivo.com',
            password='StaffPassword@123',
            is_staff=True
        )
        self.dept_account, _ = DepartmentAccount.objects.get_or_create(
            department=self.dept,
            defaults={
                'user': self.chk_user,
                'login_id': 'CHK001',
                'status': 'ACTIVE'
            }
        )
        self.dept_account.set_password('StaffPassword@123')
        self.dept_account.save()

        # Superadmin User
        self.admin = User.objects.create_superuser(
            username='cartivo_superadmin',
            email='admin@cartivo.com',
            password='AdminPassword@123'
        )

        # Catalog product
        self.cat = Category.objects.create(name='Electronics', slug='electronics')
        self.prod = Product.objects.create(
            category=self.cat,
            title='Wireless Noise-Cancelling Headphones',
            slug='wireless-headphones',
            sku='HDPH-001',
            base_price=Decimal('4999.00'),
            is_active=True
        )

        # Inventory Warehouse & Stock
        from apps.inventory.models import Warehouse
        from apps.inventory.services import InventoryService
        self.warehouse = Warehouse.objects.create(
            name='Central Distribution Center',
            code='CDC-BLR-01',
            status='ACTIVE'
        )
        stk = InventoryService.get_or_create_stock(self.prod, self.warehouse)
        stk.on_hand_quantity = 25
        stk.status = 'IN_STOCK'
        stk.save()

    def test_01_unauthenticated_access_to_dashboard_redirects(self):
        """Unauthenticated user accessing checkout dashboard redirects to portal/login."""
        res = self.client.get('/checkout/dashboard/')
        self.assertEqual(res.status_code, 302)

    def test_02_staff_access_to_dashboard_succeeds(self):
        """Checkout staff (CHK001) can access the Checkout Dashboard."""
        self.client.login(username='CHK001', password='StaffPassword@123')
        s = self.client.session
        s['department_slug'] = 'checkout'
        s.save()

        res = self.client.get('/checkout/dashboard/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Checkout Command Center')
        self.assertContains(res, 'Delivery Status Flow')

    def test_03_order_delivery_tracking_and_location_update(self):
        """Staff can view delivery detail and update location checkpoint."""
        # Create order
        cart = Cart.objects.create(user=self.customer, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.prod, quantity=1)
        order = OrderService.create_cod_order(user=self.customer, address=self.address)

        # Login as staff
        self.client.login(username='CHK001', password='StaffPassword@123')
        s = self.client.session
        s['department_slug'] = 'checkout'
        s.save()

        # View delivery detail
        res_dossier = self.client.get(f"/checkout/delivery/{order.order_number}/")
        self.assertEqual(res_dossier.status_code, 200)
        self.assertContains(res_dossier, order.order_number)
        self.assertContains(res_dossier, 'Delivery Milestone Progress')

        # Update delivery status to SHIPPED and location to regional hub
        update_data = {
            'status': 'SHIPPED',
            'delivery_partner': 'Blue Dart Express',
            'tracking_number': 'BLUEDART-AWB-998877',
            'current_location': 'South Zone Logistics Hub, Electronic City, Bengaluru',
            'estimated_delivery_date': 'Tomorrow by 4:00 PM',
            'payment_status': 'PENDING',
            'checkpoint_notes': 'Departed facility on truck #KA01-TR-900',
        }
        res_update = self.client.post(f"/checkout/delivery/{order.order_number}/update/", update_data)
        self.assertEqual(res_update.status_code, 302)

        order.refresh_from_db()
        self.assertEqual(order.status, 'SHIPPED')
        self.assertEqual(order.delivery_partner, 'Blue Dart Express')
        self.assertEqual(order.tracking_number, 'BLUEDART-AWB-998877')
        self.assertEqual(order.current_location, 'South Zone Logistics Hub, Electronic City, Bengaluru')
        self.assertEqual(order.estimated_delivery_date, 'Tomorrow by 4:00 PM')

        # Verify a new DeliveryCheckpoint was logged
        cp = order.checkpoints.filter(status='SHIPPED').first()
        self.assertIsNotNone(cp)
        self.assertEqual(cp.location, 'South Zone Logistics Hub, Electronic City, Bengaluru')
        self.assertIn('KA01-TR-900', cp.notes)

    def test_04_deliveries_search_and_filter(self):
        """Deliveries directory can filter by status and query."""
        cart = Cart.objects.create(user=self.customer, status='ACTIVE')
        CartItem.objects.create(cart=cart, product=self.prod, quantity=1)
        order = OrderService.create_cod_order(user=self.customer, address=self.address)

        self.client.login(username='cartivo_superadmin', password='AdminPassword@123')
        res = self.client.get('/checkout/deliveries/?status=CONFIRMED')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, order.order_number)

        # Search by non-matching query returns 0 matches
        res_empty = self.client.get('/checkout/deliveries/?q=NONEXISTENT_XYZ')
        self.assertEqual(res_empty.status_code, 200)
        self.assertContains(res_empty, 'No shipments found')
