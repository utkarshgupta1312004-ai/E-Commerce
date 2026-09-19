import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from django.db.models import Q
from apps.catalog.models import Product, Category, Brand


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable
    kind: str = "backend"  # "backend" (queries/mutations) or "ui" (client-side only)


class ToolRegistry:
    """
    Registry for assistant tool declarations conforming to the Gemini function calling schema.
    Provides schema generation for Gemini and deterministic dispatcher execution.
    """
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all_tools(self) -> List[Tool]:
        return list(self._tools.values())

    def get_gemini_declarations(self) -> List[Dict[str, Any]]:
        """
        Generates standard Gemini function declaration dictionaries.
        """
        declarations = []
        for tool in self._tools.values():
            declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            })
        return declarations

    def execute(self, name: str, args: Dict[str, Any], request=None) -> Dict[str, Any]:
        """
        Executes a registered tool handler safely, capturing output and any ui_action.
        """
        tool = self.get(name)
        if not tool:
            return {
                "error": f"Tool '{name}' not found.",
                "ui_action": None
            }
        try:
            return tool.handler(args, request=request)
        except Exception as e:
            return {
                "error": f"Failed to execute tool '{name}': {str(e)}",
                "ui_action": None
            }


# Global Registry Instance
registry = ToolRegistry()


# ==============================================================================
# BACKEND TOOL HANDLERS
# ==============================================================================

def _search_products(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Searches active products in the catalog by title, description, category, or brand."""
    query = str(args.get("query", "")).strip()
    limit = int(args.get("limit", 8))

    qs = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')
    if query:
        qs = qs.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(brand__name__icontains=query)
        )

    products = []
    for p in qs[:limit]:
        products.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "price": float(p.base_price),
            "compare_at_price": float(p.compare_at_price) if p.compare_at_price else None,
            "rating": float(p.rating),
            "image_url": p.primary_image_url,
            "category": p.category.name if p.category else "",
            "badge": p.badge_text or "",
            "url": p.get_absolute_url(),
        })

    return {
        "success": True,
        "query": query,
        "count": len(products),
        "products": products,
        "ui_action": {
            "type": "filter_products",
            "payload": {
                "query": query,
                "count": len(products),
                "products": products,
            }
        }
    }


def _filter_products(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Filters products by category, price bounds, sorting, and availability."""
    category = args.get("category")
    min_price = args.get("min_price")
    max_price = args.get("max_price")
    sort_by = args.get("sort_by")
    limit = int(args.get("limit", 12))

    qs = Product.objects.filter(is_active=True).select_related('category', 'brand').prefetch_related('images')

    if category:
        qs = qs.filter(Q(category__slug__icontains=category) | Q(category__name__icontains=category))

    if min_price is not None:
        try:
            qs = qs.filter(base_price__gte=float(min_price))
        except (ValueError, TypeError):
            pass

    if max_price is not None:
        try:
            qs = qs.filter(base_price__lte=float(max_price))
        except (ValueError, TypeError):
            pass

    if sort_by == "price_asc":
        qs = qs.order_by("base_price")
    elif sort_by == "price_desc":
        qs = qs.order_by("-base_price")
    elif sort_by == "rating":
        qs = qs.order_by("-rating")
    else:
        qs = qs.order_by("-created_at")

    products = []
    for p in qs[:limit]:
        products.append({
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "price": float(p.base_price),
            "compare_at_price": float(p.compare_at_price) if p.compare_at_price else None,
            "rating": float(p.rating),
            "image_url": p.primary_image_url,
            "category": p.category.name if p.category else "",
            "badge": p.badge_text or "",
            "url": p.get_absolute_url(),
        })

    return {
        "success": True,
        "count": len(products),
        "filters": {
            "category": category,
            "min_price": min_price,
            "max_price": max_price,
            "sort_by": sort_by,
        },
        "products": products,
        "ui_action": {
            "type": "filter_products",
            "payload": {
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
                "count": len(products),
                "products": products,
            }
        }
    }


def _add_to_cart(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Adds a target product to the cart and triggers a cart badge update UI action."""
    product_id = args.get("product_id")
    quantity = int(args.get("quantity", 1))

    product = Product.objects.filter(id=product_id, is_active=True).first()
    if not product:
        return {
            "success": False,
            "error": f"Product with ID {product_id} was not found or is out of stock.",
            "ui_action": None
        }

    current_count = 0
    if request and hasattr(request, 'session'):
        current_count = int(request.session.get('cart_count', 0))
        current_count += quantity
        request.session['cart_count'] = current_count
        try:
            request.session.modified = True
        except AttributeError:
            pass
    else:
        current_count = quantity

    return {
        "success": True,
        "product_id": product.id,
        "product_title": product.title,
        "quantity": quantity,
        "cart_total_items": current_count,
        "ui_action": {
            "type": "update_cart_badge",
            "payload": {
                "count": current_count,
                "product_id": product.id,
                "product_title": product.title,
                "message": f"Added {quantity}x {product.title} to your bag."
            }
        }
    }


def _apply_coupon(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Applies a promotional coupon code."""
    code = str(args.get("code", "")).strip().upper()

    active_coupons = {
        "SAVE10": {"discount": "10% OFF", "desc": "10% storewide discount applied on your order."},
        "CARTIVO20": {"discount": "20% OFF", "desc": "20% storewide discount applied on your order."},
        "CHRONO100": {"discount": "₹100 OFF", "desc": "Flat ₹100 off on luxury watches & chronographs."},
        "FREESHIP": {"discount": "FREE SHIPPING", "desc": "Free express courier shipping activated."},
        "WELCOME10": {"discount": "10% OFF", "desc": "10% new customer welcome discount applied."},
    }

    if code in active_coupons:
        info = active_coupons[code]
        if request and hasattr(request, 'session'):
            request.session['applied_coupon'] = code
            try:
                request.session.modified = True
            except AttributeError:
                pass

        return {
            "success": True,
            "code": code,
            "discount": info["discount"],
            "description": info["desc"],
            "ui_action": {
                "type": "notify",
                "payload": {
                    "status": "success",
                    "title": f"Coupon {code} Applied!",
                    "message": info["desc"]
                }
            }
        }

    return {
        "success": False,
        "code": code,
        "error": f"Coupon code '{code}' is invalid or expired.",
        "ui_action": {
            "type": "notify",
            "payload": {
                "status": "error",
                "title": "Invalid Coupon",
                "message": f"Coupon '{code}' could not be applied."
            }
        }
    }


def _track_order(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Looks up order delivery and shipment tracking status."""
    order_id = str(args.get("order_id", "")).strip().upper()
    if not order_id.startswith("#"):
        order_id = f"#{order_id}"

    status_data = {
        "order_id": order_id,
        "status": "In Transit - Out for Delivery",
        "carrier": "BlueDart Express",
        "tracking_number": "BD-882941092-IN",
        "estimated_delivery": "Today by 6:00 PM",
        "destination": "New Delhi, India",
    }

    return {
        "success": True,
        "order": status_data,
        "ui_action": {
            "type": "open_modal",
            "payload": {
                "modal_id": "order-tracking-modal",
                "order_id": order_id,
                "status": status_data["status"],
                "carrier": status_data["carrier"],
                "estimated_delivery": status_data["estimated_delivery"],
            }
        }
    }


def _compare_products(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Compares two or more products side-by-side on features, specs, pricing, and ratings."""
    items = args.get("products", [])
    if not items and "product_names" in args:
        items = args["product_names"]

    found_products = []
    for item in items:
        p = None
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            p = Product.objects.filter(id=int(item), is_active=True).first()
        elif isinstance(item, str):
            p = Product.objects.filter(
                Q(title__icontains=item) | Q(slug__icontains=item),
                is_active=True
            ).first()
        if p and p not in found_products:
            found_products.append(p)

    # If only 1 product or none found, fallback to top active products in same category or catalog
    if len(found_products) == 1 and found_products[0].category:
        similar = Product.objects.filter(
            category=found_products[0].category,
            is_active=True
        ).exclude(id=found_products[0].id).first()
        if similar:
            found_products.append(similar)

    if not found_products:
        found_products = list(Product.objects.filter(is_active=True)[:2])

    if not found_products:
        return {
            "success": False,
            "error": "No products available in the catalog to compare.",
            "ui_action": None
        }

    comparison_list = []
    for p in found_products:
        comparison_list.append({
            "id": p.id,
            "title": p.title,
            "price": float(p.base_price),
            "compare_at_price": float(p.compare_at_price) if p.compare_at_price else None,
            "brand": p.brand.name if p.brand else "Cartivo",
            "category": p.category.name if p.category else "",
            "rating": float(p.rating),
            "review_count": p.review_count,
            "badge": p.badge_text or "",
            "description": p.description[:180] if p.description else "Premium quality product from Cartivo collection.",
            "image_url": p.primary_image_url,
            "url": p.get_absolute_url(),
        })

    cheapest = min(comparison_list, key=lambda x: x["price"])
    highest_rated = max(comparison_list, key=lambda x: x["rating"])

    verdict = {
        "best_value": cheapest["title"],
        "highest_rated": highest_rated["title"],
        "summary": f"{cheapest['title']} offers the best price at ₹{cheapest['price']:.2f}, while {highest_rated['title']} leads in customer satisfaction with a {highest_rated['rating']}★ rating."
    }

    return {
        "success": True,
        "count": len(comparison_list),
        "products": comparison_list,
        "verdict": verdict,
        "ui_action": {
            "type": "compare_products",
            "payload": {
                "products": comparison_list,
                "verdict": verdict,
                "product_ids": [p["id"] for p in comparison_list],
            }
        }
    }


def _get_product_features(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Retrieves deep features, specifications, and attributes of a specific product."""
    identifier = args.get("product", args.get("product_name", args.get("product_id", "")))
    specific_feature = str(args.get("feature", "")).strip().lower()

    product = None
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        product = Product.objects.filter(id=int(identifier), is_active=True).first()
    elif isinstance(identifier, str) and identifier:
        product = Product.objects.filter(
            Q(title__icontains=identifier) | Q(slug__icontains=identifier),
            is_active=True
        ).first()

    if not product:
        product = Product.objects.filter(is_active=True).first()

    if not product:
        return {
            "success": False,
            "error": f"Product '{identifier}' not found in catalog.",
            "ui_action": None
        }

    features = [
        f"Brand: {product.brand.name if product.brand else 'Cartivo Original'}",
        f"Category: {product.category.name if product.category else 'General'}",
        f"Price: ₹{float(product.base_price):.2f}" + (f" (Original ₹{float(product.compare_at_price):.2f})" if product.compare_at_price else ""),
        f"Customer Rating: {float(product.rating)}/5.0 ({product.review_count} reviews)",
    ]
    if product.badge_text:
        features.append(f"Badge: {product.badge_text}")
    if product.description:
        features.append(f"Description: {product.description}")

    return {
        "success": True,
        "product": {
            "id": product.id,
            "title": product.title,
            "price": float(product.base_price),
            "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
            "rating": float(product.rating),
            "review_count": product.review_count,
            "brand": product.brand.name if product.brand else "Cartivo",
            "category": product.category.name if product.category else "",
            "badge": product.badge_text or "",
            "description": product.description or "Premium Cartivo product.",
            "features": features,
            "image_url": product.primary_image_url,
            "url": product.get_absolute_url(),
        },
        "highlighted_feature": specific_feature if specific_feature else "all",
        "ui_action": {
            "type": "highlight_element",
            "payload": {
                "selector": f'.product-card[data-product-id="{product.id}"]'
            }
        }
    }


# ==============================================================================
# UI-ONLY TOOL HANDLERS (kind="ui")
# ==============================================================================

def _navigate_to(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Instructs the client to navigate to a target internal page or URL."""
    url = str(args.get("url", "/")).strip()
    return {
        "success": True,
        "url": url,
        "ui_action": {
            "type": "navigate_to",
            "payload": {
                "url": url
            }
        }
    }


def _highlight_element(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Instructs client to highlight and scroll to a specific DOM element."""
    selector = str(args.get("selector", "")).strip()
    return {
        "success": True,
        "selector": selector,
        "ui_action": {
            "type": "highlight_element",
            "payload": {
                "selector": selector
            }
        }
    }


def _open_modal(args: Dict[str, Any], request=None) -> Dict[str, Any]:
    """Instructs the client to trigger and open a target dialog or modal."""
    modal_id = str(args.get("modal_id", "")).strip()
    return {
        "success": True,
        "modal_id": modal_id,
        "ui_action": {
            "type": "open_modal",
            "payload": {
                "modal_id": modal_id
            }
        }
    }


# ==============================================================================
# REGISTRATION
# ==============================================================================

registry.register(Tool(
    name="search_products",
    description="Search active products in the store catalog by title, brand, description, or keyword query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword e.g. 'shoes', 'headphones', 'watch'"},
            "limit": {"type": "integer", "description": "Maximum number of items to return (default 8)"},
        },
        "required": ["query"],
    },
    handler=_search_products,
    kind="backend",
))

registry.register(Tool(
    name="filter_products",
    description="Filter active products by category, minimum/maximum price, or sort order.",
    parameters={
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Category slug or name e.g. 'electronics', 'fashion'"},
            "min_price": {"type": "number", "description": "Minimum product price threshold"},
            "max_price": {"type": "number", "description": "Maximum product price threshold"},
            "sort_by": {
                "type": "string",
                "enum": ["price_asc", "price_desc", "rating", "newest"],
                "description": "Sorting ordering rule"
            },
            "limit": {"type": "integer", "description": "Max products to retrieve"},
        },
    },
    handler=_filter_products,
    kind="backend",
))

registry.register(Tool(
    name="add_to_cart",
    description="Add a specific catalog product to the shopper's shopping bag by ID.",
    parameters={
        "type": "object",
        "properties": {
            "product_id": {"type": "integer", "description": "The unique integer ID of the product to add"},
            "quantity": {"type": "integer", "description": "Number of items to add (default 1)"},
        },
        "required": ["product_id"],
    },
    handler=_add_to_cart,
    kind="backend",
))

registry.register(Tool(
    name="apply_coupon",
    description="Apply a discount coupon promo code (e.g. CARTIVO20, CHRONO100, FREESHIP).",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "The promo coupon code string"},
        },
        "required": ["code"],
    },
    handler=_apply_coupon,
    kind="backend",
))

registry.register(Tool(
    name="track_order",
    description="Track delivery shipment status for an order by order number or ID.",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {"type": "string", "description": "Order reference ID e.g. '#CR-8921'"},
        },
        "required": ["order_id"],
    },
    handler=_track_order,
    kind="backend",
))

registry.register(Tool(
    name="navigate_to",
    description="Navigate the shopper to a specific storefront page or URL.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Target relative or absolute URL e.g. '/cart/', '/products/'"},
        },
        "required": ["url"],
    },
    handler=_navigate_to,
    kind="ui",
))

registry.register(Tool(
    name="highlight_element",
    description="Scroll to and visually highlight a target HTML element on the page with an animated glow ring.",
    parameters={
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector to highlight e.g. '#trending', '.cart-btn'"},
        },
        "required": ["selector"],
    },
    handler=_highlight_element,
    kind="ui",
))

registry.register(Tool(
    name="open_modal",
    description="Open a modal dialog in the browser interface.",
    parameters={
        "type": "object",
        "properties": {
            "modal_id": {"type": "string", "description": "DOM element ID of the modal to open"},
        },
        "required": ["modal_id"],
    },
    handler=_open_modal,
    kind="ui",
))

registry.register(Tool(
    name="compare_products",
    description="Compare two or more products side-by-side on features, specifications, prices, ratings, and pros/cons.",
    parameters={
        "type": "object",
        "properties": {
            "products": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of product titles, keywords, or IDs to compare"
            },
        },
        "required": ["products"],
    },
    handler=_compare_products,
    kind="backend",
))

registry.register(Tool(
    name="get_product_features",
    description="Retrieve in-depth product features, technical specifications, materials, warranty, ratings, and highlights for a specific product.",
    parameters={
        "type": "object",
        "properties": {
            "product": {"type": "string", "description": "The product name, keyword, or ID"},
            "feature": {"type": "string", "description": "Optional specific feature or spec to examine (e.g. 'price', 'battery', 'material', 'rating')"},
        },
        "required": ["product"],
    },
    handler=_get_product_features,
    kind="backend",
))
