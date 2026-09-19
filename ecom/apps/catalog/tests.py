from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.catalog.models import (
    Category,
    Brand,
    Product,
    ProductVariant,
    ProductTag,
    Attribute,
    AttributeValue,
    VariantAttributeValue,
)
from apps.core.models import ManagementDepartment, DepartmentAccount

User = get_user_model()


class CatalogModelTests(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Bang & Olufsen", slug="bang-olufsen")
        self.category = Category.objects.create(name="Audio", slug="audio")

    def test_category_self_parent_validation(self):
        """A category cannot be its own parent."""
        self.category.parent = self.category
        with self.assertRaises(ValidationError):
            self.category.clean()

    def test_category_hierarchy_cycle_prevention(self):
        """Category cycles (A -> B -> A) must be detected and rejected."""
        sub_cat = Category.objects.create(name="Headphones", slug="headphones", parent=self.category)
        self.category.parent = sub_cat
        with self.assertRaises(ValidationError):
            self.category.clean()

    def test_brand_logo_fallback(self):
        """Brand effective_logo_url returns logo_url or empty string gracefully."""
        self.assertEqual(self.brand.effective_logo_url, "")
        self.brand.logo_url = "https://example.com/logo.png"
        self.assertEqual(self.brand.effective_logo_url, "https://example.com/logo.png")

    def test_product_pricing_and_discount(self):
        """Discount percentage computes precisely based on compare_at_price."""
        product = Product.objects.create(
            title="Beoplay H95",
            slug="beoplay-h95",
            category=self.category,
            brand=self.brand,
            sku="BEO-H95-001",
            base_price=Decimal("800.00"),
            compare_at_price=Decimal("1000.00"),
            status="ACTIVE",
            visibility="PUBLIC"
        )
        self.assertEqual(product.discount_percentage, Decimal("20.0"))
        self.assertEqual(product.effective_price, Decimal("800.00"))
        self.assertEqual(product.name, "Beoplay H95")

    def test_product_variants_and_attributes(self):
        """Variants support unique SKUs and attribute values."""
        product = Product.objects.create(
            title="Beoplay Portal",
            slug="beoplay-portal",
            category=self.category,
            brand=self.brand,
            sku="BEO-PORTAL-BASE",
            base_price=Decimal("500.00"),
            status="ACTIVE"
        )
        color_attr = Attribute.objects.create(name="Color", code="color")
        val_black = AttributeValue.objects.create(attribute=color_attr, value="Black")
        val_navy = AttributeValue.objects.create(attribute=color_attr, value="Navy")

        v1 = ProductVariant.objects.create(
            product=product,
            sku="BEO-PORTAL-BLK",
            name="Black",
            price=Decimal("499.00")
        )
        VariantAttributeValue.objects.create(variant=v1, attribute=color_attr, attribute_value=val_black)

        self.assertEqual(v1.effective_price, Decimal("499.00"))
        self.assertEqual(v1.attribute_values.count(), 1)


class CatalogStorefrontViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name="Smartphones", slug="smartphones", is_active=True)
        self.brand = Brand.objects.create(name="Apple", slug="apple", is_active=True)

        self.active_product = Product.objects.create(
            title="iPhone 15 Pro",
            slug="iphone-15-pro",
            category=self.category,
            brand=self.brand,
            sku="APL-IPH15P-128",
            base_price=Decimal("999.00"),
            status="ACTIVE",
            visibility="PUBLIC",
            is_active=True
        )
        self.draft_product = Product.objects.create(
            title="iPhone 16 Prototype",
            slug="iphone-16-proto",
            category=self.category,
            brand=self.brand,
            sku="APL-IPH16-DRAFT",
            base_price=Decimal("1199.00"),
            status="DRAFT",
            visibility="PUBLIC",
            is_active=False
        )

    def test_product_list_hides_drafts_from_customers(self):
        """Storefront product list exposes only active public items."""
        response = self.client.get(reverse('catalog:product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iPhone 15 Pro")
        self.assertNotContains(response, "iPhone 16 Prototype")

    def test_product_list_filtering_by_brand(self):
        """Filtering by brand returns only products of that brand."""
        response = self.client.get(reverse('catalog:product_list') + f"?brand={self.brand.slug}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iPhone 15 Pro")

    def test_product_detail_view_success(self):
        """Active product detail view renders successfully with JSON variant matrix."""
        response = self.client.get(reverse('catalog:product_detail', kwargs={'slug': self.active_product.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iPhone 15 Pro")
        self.assertIn('variants_json', response.context)
        self.assertContains(response, 'id="unit-price-indicator"')
        self.assertContains(response, 'id="stock-badge"')
        self.assertContains(response, 'id="btn-buy-now"')

    def test_product_detail_variant_json_payload(self):
        """Variant matrix in product detail context contains database prices and stock info."""
        import json
        color = Attribute.objects.create(name="Color", code="color")
        val_blue = AttributeValue.objects.create(attribute=color, value="Titanium Blue")
        v = ProductVariant.objects.create(
            product=self.active_product,
            sku="APL-IPH15P-BLU",
            name="Titanium Blue",
            price=Decimal("1099.00"),
        )
        VariantAttributeValue.objects.create(variant=v, attribute=color, attribute_value=val_blue)

        response = self.client.get(reverse('catalog:product_detail', kwargs={'slug': self.active_product.slug}))
        self.assertEqual(response.status_code, 200)
        variants_data = json.loads(response.context['variants_json'])
        self.assertEqual(len(variants_data), 1)
        self.assertEqual(variants_data[0]['sku'], "APL-IPH15P-BLU")
        self.assertEqual(variants_data[0]['price'], "1099.00")
        self.assertEqual(variants_data[0]['attributes']['Color'], "Titanium Blue")
        self.assertIn('available_stock', variants_data[0])
        self.assertIn('is_in_stock', variants_data[0])

    def test_product_detail_draft_hidden_for_anonymous(self):
        """Draft products return 404 for customers."""
        response = self.client.get(reverse('catalog:product_detail', kwargs={'slug': self.draft_product.slug}))
        self.assertEqual(response.status_code, 404)

    def test_category_detail_route_filters_products(self):
        """Category route /category/<slug>/ filters products by category."""
        other_cat = Category.objects.create(name="Shoes", slug="shoes", is_active=True)
        response = self.client.get(reverse('catalog:category_detail', kwargs={'slug': 'smartphones'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "iPhone 15 Pro")

        empty_cat_response = self.client.get(reverse('catalog:category_detail', kwargs={'slug': 'shoes'}))
        self.assertEqual(empty_cat_response.status_code, 200)
        self.assertNotContains(empty_cat_response, "iPhone 15 Pro")


class CatalogManagementSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username="admin_catalog_test",
            email="admin@cartivo.com",
            password="securepassword123"
        )
        self.category = Category.objects.create(name="Horology", slug="horology", is_active=True)

    def test_anonymous_access_to_dashboard_blocked(self):
        """Unauthenticated requests to management console are redirected."""
        response = self.client.get(reverse('catalog:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_superadmin_access_to_dashboard_allowed(self):
        """Superusers can access the Catalog Console."""
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('catalog:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catalog Dashboard")

    def test_superadmin_product_creation(self):
        """Superuser can create new products via management console."""
        self.client.force_login(self.admin_user)
        post_data = {
            'action_type': 'update_product',
            'title': 'Omega Speedmaster Professional',
            'slug': 'omega-speedmaster-pro',
            'category': self.category.id,
            'sku': 'OMG-SPEEDY-01',
            'base_price': '7600.00',
            'status': 'ACTIVE',
            'visibility': 'PUBLIC',
        }
        response = self.client.post(reverse('catalog:product_add'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(sku='OMG-SPEEDY-01').exists())
