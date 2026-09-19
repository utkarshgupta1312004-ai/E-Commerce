from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import Product, Category
from apps.inventory.models import (
    Warehouse,
    Location,
    Stock,
    StockMovement,
    StockReservation,
    StockAdjustment,
)
from apps.inventory.services import (
    InventoryService,
    InsufficientStockError,
    StockValidationError,
)

User = get_user_model()


class InventoryServiceTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            title="Premium Wireless Headphones",
            slug="premium-wireless-headphones",
            sku="WH-AUDIO-001",
            base_price=Decimal("199.99"),
            category=self.category,
            status="ACTIVE",
            visibility="PUBLIC",
            is_active=True,
        )
        self.warehouse_a = Warehouse.objects.create(
            code="WH-EAST",
            name="East Coast Fulfillment",
            is_primary=True,
            status="ACTIVE",
        )
        self.warehouse_b = Warehouse.objects.create(
            code="WH-WEST",
            name="West Coast Fulfillment",
            is_primary=False,
            status="ACTIVE",
        )

    def test_stock_increase_and_ledger(self):
        """Increasing stock updates physical balance and creates StockMovement audit."""
        stock = InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=20,
            movement_type='PURCHASE_RECEIPT',
            reason='Initial shipment arrival',
        )
        self.assertEqual(stock.on_hand_quantity, 20)
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.available_quantity, 20)
        self.assertEqual(stock.status, 'IN_STOCK')

        # Check movement ledger
        movement = StockMovement.objects.filter(product=self.product, warehouse=self.warehouse_a).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.movement_type, 'PURCHASE_RECEIPT')
        self.assertEqual(movement.quantity, 20)
        self.assertEqual(movement.before_quantity, 0)
        self.assertEqual(movement.after_quantity, 20)

    def test_stock_decrease(self):
        """Decreasing stock updates physical balance and records sale movement."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=15,
        )
        stock = InventoryService.decrease_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=5,
            movement_type='SALE',
            reference_id='ORD-101',
        )
        self.assertEqual(stock.on_hand_quantity, 10)
        self.assertEqual(stock.available_quantity, 10)

        # Check ledger
        movement = StockMovement.objects.filter(product=self.product, movement_type='SALE').first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity, -5)
        self.assertEqual(movement.before_quantity, 15)
        self.assertEqual(movement.after_quantity, 10)

    def test_insufficient_stock_error(self):
        """Cannot decrease stock below available quantity."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=3,
        )
        with self.assertRaises(InsufficientStockError):
            InventoryService.decrease_stock(
                product=self.product,
                warehouse=self.warehouse_a,
                quantity=10,
            )

    def test_stock_reservation_and_release(self):
        """Holds stock without altering physical on_hand; releasing restores available stock."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=10,
        )
        # Reserve 4 units
        res = InventoryService.reserve_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=4,
            reference_type='ORDER',
            reference_id='ORD-202',
        )
        stock = Stock.objects.get(pk=res.stock_id)
        self.assertEqual(stock.on_hand_quantity, 10)
        self.assertEqual(stock.reserved_quantity, 4)
        self.assertEqual(stock.available_quantity, 6)

        # Release reservation
        InventoryService.release_reservation(reservation=res)
        stock.refresh_from_db()
        self.assertEqual(stock.on_hand_quantity, 10)
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.available_quantity, 10)

        res.refresh_from_db()
        self.assertEqual(res.status, 'RELEASED')

    def test_stock_reservation_and_fulfillment(self):
        """Fulfilling reservation deducts physical stock and clears reservation."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=10,
        )
        res = InventoryService.reserve_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=3,
            reference_type='ORDER',
            reference_id='ORD-303',
        )
        InventoryService.fulfill_reservation(reservation=res)

        stock = Stock.objects.get(pk=res.stock_id)
        self.assertEqual(stock.on_hand_quantity, 7)
        self.assertEqual(stock.reserved_quantity, 0)
        self.assertEqual(stock.available_quantity, 7)

        res.refresh_from_db()
        self.assertEqual(res.status, 'FULFILLED')

    def test_stock_purchase_decreases_to_zero_and_shows_out_of_stock(self):
        """When bought, stock decreases; when zero, it shows OUT_OF_STOCK and disables purchase."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=2,
        )
        self.assertTrue(self.product.is_in_stock)
        self.assertEqual(self.product.total_available_stock, 2)

        # Buy 1 unit
        InventoryService.purchase_product(product=self.product, quantity=1)
        self.assertEqual(self.product.total_available_stock, 1)
        self.assertTrue(self.product.is_in_stock)

        # Buy 2nd unit -> reaches zero
        stock = InventoryService.purchase_product(product=self.product, quantity=1)
        self.assertEqual(stock.on_hand_quantity, 0)
        self.assertEqual(stock.available_quantity, 0)
        self.assertEqual(stock.status, 'OUT_OF_STOCK')

        self.assertFalse(self.product.is_in_stock)
        self.assertEqual(self.product.total_available_stock, 0)

        # Attempt to buy again when zero -> InsufficientStockError
        with self.assertRaises(InsufficientStockError):
            InventoryService.purchase_product(product=self.product, quantity=1)

    def test_stock_adjustment(self):
        """Manual adjustments (SET, INCREASE, DECREASE) correctly update stock and audit."""
        InventoryService.adjust_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            adjustment_type='SET',
            quantity=25,
            reason='CYCLE_COUNT',
            notes='Quarterly physical count',
        )
        stock = Stock.objects.get(product=self.product, warehouse=self.warehouse_a)
        self.assertEqual(stock.on_hand_quantity, 25)

        InventoryService.adjust_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            adjustment_type='DECREASE',
            quantity=5,
            reason='DAMAGED',
            notes='Water damage in warehouse',
        )
        stock.refresh_from_db()
        self.assertEqual(stock.on_hand_quantity, 20)

    def test_stock_transfer_between_warehouses(self):
        """Inter-warehouse transfer deducts origin and adds to destination."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=10,
        )
        InventoryService.transfer_stock(
            product=self.product,
            source_warehouse=self.warehouse_a,
            dest_warehouse=self.warehouse_b,
            quantity=4,
            reason='Regional stock rebalance',
        )
        stock_a = Stock.objects.get(product=self.product, warehouse=self.warehouse_a)
        stock_b = Stock.objects.get(product=self.product, warehouse=self.warehouse_b)

        self.assertEqual(stock_a.on_hand_quantity, 6)
        self.assertEqual(stock_b.on_hand_quantity, 4)

    def test_storefront_buy_view_and_out_of_stock_display(self):
        """Storefront POST /products/<slug>/buy/ decreases stock; when 0, detail page reflects out of stock."""
        InventoryService.increase_stock(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=1,
        )
        client = Client()

        # Check detail page before purchase (In Stock)
        resp = client.get(reverse('catalog:product_detail', kwargs={'slug': self.product.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Buy Now")
        self.assertNotContains(resp, "<span>Out of Stock</span>")

        # Buy the only 1 unit in stock
        buy_url = reverse('catalog:product_buy', kwargs={'slug': self.product.slug})
        post_resp = client.post(buy_url, {'quantity': '1'}, follow=True)
        self.assertEqual(post_resp.status_code, 200)
        self.assertContains(post_resp, "OUT OF STOCK")

        # Now stock is 0; check product detail page shows Out of Stock
        detail_resp = client.get(reverse('catalog:product_detail', kwargs={'slug': self.product.slug}))
        self.assertContains(detail_resp, "<span>Out of Stock</span>")
        self.assertContains(detail_resp, "disabled")
