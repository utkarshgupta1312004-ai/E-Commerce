import json
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, RequestFactory
from django.core.cache import cache
from django.contrib.auth import get_user_model

from apps.catalog.models import Category, Brand, Product
from apps.assistant.models import ChatSession, ChatMessage
from apps.assistant.tools import registry, ToolRegistry
from apps.assistant.gemini_client import GeminiAssistantClient
from apps.audit.models import AuditLog

User = get_user_model()


class AssistantToolsTest(TestCase):
    """
    Tests for the ToolRegistry and specific tool handlers.
    """

    def setUp(self):
        self.category = Category.objects.create(name="Shoes", slug="shoes")
        self.brand = Brand.objects.create(name="Nike", slug="nike")
        self.product1 = Product.objects.create(
            title="Air Max Runner",
            slug="air-max-runner",
            category=self.category,
            brand=self.brand,
            base_price=Decimal("89.99"),
            is_active=True,
        )
        self.product2 = Product.objects.create(
            title="Pro Leather Sneaker",
            slug="pro-leather-sneaker",
            category=self.category,
            brand=self.brand,
            base_price=Decimal("150.00"),
            is_active=True,
        )

    def test_registry_contains_required_tools(self):
        tools = [t.name for t in registry.all_tools()]
        expected = [
            "search_products",
            "filter_products",
            "add_to_cart",
            "apply_coupon",
            "track_order",
            "navigate_to",
            "highlight_element",
            "open_modal",
        ]
        for name in expected:
            self.assertIn(name, tools)

    def test_search_products_tool(self):
        res = registry.execute("search_products", {"query": "Runner"})
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["products"][0]["title"], "Air Max Runner")
        self.assertIsNotNone(res["ui_action"])
        self.assertEqual(res["ui_action"]["type"], "filter_products")

    def test_filter_products_tool_by_price(self):
        res = registry.execute("filter_products", {"max_price": 100})
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["products"][0]["id"], self.product1.id)

    def test_add_to_cart_tool(self):
        factory = RequestFactory()
        request = factory.post("/fake/")
        # Mock session
        request.session = {}

        res = registry.execute("add_to_cart", {"product_id": self.product1.id, "quantity": 2}, request=request)
        self.assertTrue(res["success"])
        self.assertEqual(res["cart_total_items"], 2)
        self.assertIsNotNone(res["ui_action"])
        self.assertEqual(res["ui_action"]["type"], "update_cart_badge")
        self.assertEqual(res["ui_action"]["payload"]["count"], 2)

    def test_apply_coupon_tool(self):
        # Valid coupon
        res = registry.execute("apply_coupon", {"code": "SAVE10"})
        self.assertTrue(res["success"])
        self.assertEqual(res["discount"], "10% OFF")

        # Invalid coupon
        res_invalid = registry.execute("apply_coupon", {"code": "FAKECODE"})
        self.assertFalse(res_invalid["success"])

    def test_track_order_tool(self):
        res = registry.execute("track_order", {"order_id": "ORD-12345"})
        self.assertEqual(res["order"]["order_id"], "#ORD-12345")
        self.assertIn("status", res["order"])

    def test_compare_products_tool(self):
        res = registry.execute("compare_products", {"products": ["Air Max", "Pro Leather"]})
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 2)
        self.assertIn("verdict", res)
        self.assertEqual(res["ui_action"]["type"], "compare_products")
        self.assertEqual(len(res["ui_action"]["payload"]["product_ids"]), 2)

    def test_get_product_features_tool(self):
        res = registry.execute("get_product_features", {"product": "Air Max"})
        self.assertTrue(res["success"])
        self.assertEqual(res["product"]["id"], self.product1.id)
        self.assertTrue(len(res["product"]["features"]) >= 3)
        self.assertEqual(res["ui_action"]["type"], "highlight_element")

    def test_ui_tools(self):
        nav_res = registry.execute("navigate_to", {"url": "/cart/", "new_tab": False})
        self.assertEqual(nav_res["ui_action"]["type"], "navigate_to")

        highlight_res = registry.execute("highlight_element", {"selector": "#cart-badge"})
        self.assertEqual(highlight_res["ui_action"]["type"], "highlight_element")

        modal_res = registry.execute("open_modal", {"modal_id": "coupon-modal"})
        self.assertEqual(modal_res["ui_action"]["type"], "open_modal")


class AssistantMessageViewTest(TestCase):
    """
    Tests for POST /api/assistant/message/ API endpoint.
    """

    def setUp(self):
        cache.clear()
        self.client = Client()

    def tearDown(self):
        cache.clear()

    def test_empty_message_returns_bad_request(self):
        response = self.client.post(
            "/api/assistant/message/",
            data=json.dumps({"message": "   "}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_successful_message_turn_fallback(self):
        response = self.client.post(
            "/api/assistant/message/",
            data=json.dumps({"message": "Hello, can you help me?"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_id", data)
        self.assertIn("reply", data)
        self.assertIn("actions", data)

        # Check DB persistence
        session = ChatSession.objects.filter(session_id=data["session_id"]).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.messages.count(), 2)  # 1 user + 1 assistant

    def test_message_turn_with_product_query(self):
        Category.objects.create(name="Shoes", slug="shoes-test")
        Product.objects.create(
            title="Running Sneakers",
            slug="running-sneakers",
            category=Category.objects.get(slug="shoes-test"),
            base_price=Decimal("49.99"),
            is_active=True
        )

        response = self.client.post(
            "/api/assistant/message/",
            data=json.dumps({"message": "find shoes under 60"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data["actions"]) > 0)
        self.assertEqual(data["actions"][0]["type"], "filter_products")

    def test_rate_limiting(self):
        # 20 requests allowed per window - mock send_message to test rate limit quickly
        with patch.object(GeminiAssistantClient, 'send_message', return_value=("Echo", [], [], [])):
            for i in range(20):
                res = self.client.post(
                    "/api/assistant/message/",
                    data=json.dumps({"message": f"Ping {i}"}),
                    content_type="application/json"
                )
                self.assertEqual(res.status_code, 200)

            # 21st request should be throttled
            throttled_res = self.client.post(
                "/api/assistant/message/",
                data=json.dumps({"message": "Ping 21"}),
                content_type="application/json"
            )
            self.assertEqual(throttled_res.status_code, 429)

    def test_backend_tool_triggers_audit_log(self):
        Category.objects.create(name="Electronics", slug="electronics-test")
        Product.objects.create(
            title="Wireless Earbuds",
            slug="wireless-earbuds",
            category=Category.objects.get(slug="electronics-test"),
            base_price=Decimal("35.00"),
            is_active=True
        )

        # Apply coupon triggers apply_coupon backend tool
        response = self.client.post(
            "/api/assistant/message/",
            data=json.dumps({"message": "Apply promo code SAVE10"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

        # Check AuditLog
        logs = AuditLog.objects.filter(department="assistant")
        self.assertTrue(logs.exists())
        self.assertIn("assistant_tool_apply_coupon", [l.action for l in logs])

    def test_message_turn_with_browser_context_and_comparison(self):
        cat = Category.objects.create(name="Watches", slug="watches-comp")
        p1 = Product.objects.create(
            title="Chrono Alpha",
            slug="chrono-alpha",
            category=cat,
            base_price=Decimal("199.00"),
            rating=Decimal("4.8"),
            is_active=True
        )
        p2 = Product.objects.create(
            title="Chrono Beta",
            slug="chrono-beta",
            category=cat,
            base_price=Decimal("149.00"),
            rating=Decimal("4.5"),
            is_active=True
        )

        browser_ctx = {
            "url": "/products/chrono-alpha/",
            "page_title": "Chrono Alpha Watch",
            "cart_count": 1,
            "visible_products": [
                {"id": p1.id, "title": "Chrono Alpha", "price": "199.00"},
                {"id": p2.id, "title": "Chrono Beta", "price": "149.00"}
            ]
        }

        response = self.client.post(
            "/api/assistant/message/",
            data=json.dumps({
                "message": "compare Chrono Alpha vs Chrono Beta",
                "browser_context": browser_ctx
            }),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Comparison", data["reply"])
        self.assertTrue(len(data["actions"]) > 0)
        self.assertEqual(data["actions"][0]["type"], "compare_products")

    def test_message_turn_with_product_features(self):
        cat = Category.objects.create(name="Audio", slug="audio-feat")
        Product.objects.create(
            title="Studio ANC Pro",
            slug="studio-anc-pro",
            category=cat,
            base_price=Decimal("299.00"),
            description="High-end noise canceling over-ear headphones with 40-hour battery life.",
            is_active=True
        )

        response = self.client.post(
            "/api/assistant/message/",
            data=json.dumps({"message": "what are the features of Studio ANC Pro"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Features", data["reply"])
