# Development Rules, Libraries & Coding Standards

## Project: Next-Generation Modern E-Commerce Platform

---

## 1. Approved Technology Stack & Libraries

### 1.1. Core Backend & Framework

| Package / Dependency   | Target Version | Primary Purpose                              |
| :--------------------- | :------------- | :------------------------------------------- |
| **Python**             | `3.12+`        | Runtime environment                          |
| **Django**             | `5.1.x / 5.2`  | Core web framework                           |
| **psycopg[binary]**    | `3.2.x`        | Modern PostgreSQL database adapter           |
| **django-environ**     | `0.11.x`       | Twelve-factor `.env` configuration           |
| **Pillow**             | `10.x`         | Image processing, resizing & WebP conversion |
| **redis**              | `5.0.x`        | Python client for Redis caching & broker     |
| **celery**             | `5.4.x`        | Asynchronous task queue & background workers |
| **django-celery-beat** | `2.6.x`        | Database-backed periodic task scheduler      |

### 1.2. Payments & Third-Party Integrations

| Package / Dependency               | Primary Purpose                                          |
| :--------------------------------- | :------------------------------------------------------- |
| **stripe**                         | Official Stripe Python SDK for Card/Apple Pay/Google Pay |
| **razorpay**                       | Razorpay Python client for UPI, Cards & Netbanking       |
| **reportlab**                      | High-performance PDF invoice generation                  |
| **django-storages** (with `boto3`) | AWS S3 / Cloudflare R2 media storage (production)        |

### 1.3. Frontend & UI Layer

| Technology / Asset                    | Usage Guideline                                                                                  |
| :------------------------------------ | :----------------------------------------------------------------------------------------------- |
| **Django Templates (DTL)**            | Clean, semantic server-rendered markup with template inheritance                                 |
| **Vanilla CSS3 (Design Tokens)**      | Custom CSS variables defined in `design.md`; zero heavy external CSS frameworks unless requested |
| **Alpine.js (v3.x via CDN/Vendored)** | Lightweight reactive micro-interactions (cart drawer, modals, dropdowns, tabs)                   |
| **HTMX (v1.9+ optional)**             | Dynamic partial page updates (live filter updates, instant cart badge increment)                 |
| **Lucide Icons / Feather Icons**      | Clean, minimalist SVG iconography                                                                |

---

## 2. Architectural & Code Organization Rules

### 2.1. Layered Architecture Discipline

To keep code maintainable and prevent "Fat Models / Fat Views", code within every app must adhere to this file structure:

```
apps/<app_name>/
├── models.py       # Pure schema definitions, clean field validators, simple properties
├── services.py     # ALL business actions, state changes, external calls, payment logic
├── selectors.py    # Complex queries, filters, data aggregations, ORM optimization
├── views.py        # Thin controllers: parse request -> call service/selector -> return response
├── forms.py        # Django forms & validation logic
├── urls.py         # URL routes for the domain
├── tasks.py        # Asynchronous Celery background jobs
├── signals.py      # Only for decoupled side-effects (e.g., clearing caches)
└── admin.py        # Clean admin dashboards with list filters and search
```

### 2.2. Approved 20 Modular Domain Apps & Template Mapping

Each domain belongs to its dedicated app under `apps/`, and its templates must reside in `templates/<app_name>/<template_name>.html`:

| App Name | Domain Data | Dashboard Metrics | Templates (`templates/<app>/`) |
| :--- | :--- | :--- | :--- |
| `accounts` | Users, profiles, addresses, roles | Total users, active, new, blocked | `login`, `register`, `profile`, `users`, `user_detail` |
| `catalog` | Products, categories, brands, variants | Total products, categories, active, out-of-stock | `products`, `product_detail`, `categories`, `brands`, `variants` |
| `inventory` | Stock, warehouses, stock movements | Total stock, low stock, out of stock, reserved stock | `inventory`, `stock_detail`, `warehouses`, `stock_movements` |
| `search` | Search queries, filters, search results | Popular searches, zero-result searches, trends | `search`, `search_results`, `search_analytics` |
| `cart` | Carts, cart items, abandoned carts | Active carts, abandoned carts, cart value, conversion | `cart`, `cart_detail`, `abandoned_carts` |
| `wishlist` | Wishlists, wishlist items | Total wishlists, popular products, conversions | `wishlist`, `wishlist_detail` |
| `checkout` | Checkout sessions, addresses, shipping | Active checkouts, completed, abandoned | `checkout`, `address`, `shipping`, `review` |
| `payments` | Transactions, payment methods, refunds | Successful, failed, pending, refunds | `payments`, `transaction_detail`, `refunds` |
| `orders` | Orders, order items, status, history | Total orders, pending, processing, shipped, delivered, cancelled | `orders`, `order_detail`, `order_invoice` |
| `shipping` | Shipments, carriers, tracking, zones | Pending shipments, shipped, in-transit, delivered, delayed | `shipments`, `shipment_detail`, `tracking`, `carriers` |
| `fulfillment`| Picking, packing, fulfillment tasks | Pending fulfillment, picking, packing, ready to ship | `fulfillment`, `picking`, `packing`, `tasks` |
| `promotions` | Coupons, discounts, campaigns | Active offers, coupon usage, discount amount, revenue | `promotions`, `coupons`, `campaigns`, `promotion_detail` |
| `reviews` | Reviews, ratings, moderation | Total reviews, average rating, pending/reported | `reviews`, `review_detail`, `moderation` |
| `notifications`| Email, SMS, push notifications, templates| Sent, delivered, failed, opened | `notifications`, `templates`, `notification_detail` |
| `recommendations`| Product recommendations, rules | Clicks, CTR, attributed revenue | `recommendations`, `rules`, `recommendation_analytics` |
| `cms` | Pages, banners, menus, content blocks | Published pages, banners, drafts, scheduled content | `pages`, `page_editor`, `banners`, `menus` |
| `analytics` | Sales, customers, products, metrics | Revenue, sales, conversion, AOV, customer analytics | `dashboard`, `sales`, `customers`, `products`, `reports` |
| `support` | Tickets, customer queries, complaints | Open tickets, pending, resolved, response time | `tickets`, `ticket_detail`, `customers`, `knowledge_base` |
| `audit` | Admin actions, login activity, system events | Recent activities, security events, admin actions | `logs`, `activity_detail`, `security_events` |
| `settings` | Store, payment, and shipping settings | Store configuration status | `settings`, `general`, `payment`, `shipping`, `email` |

### 2.3. Service Layer Rule

- **Rule:** Never put checkout math, payment gateway calls, or multi-table updates directly into a view function or class-based view.
- **Implementation:** Always delegate to `services.py` (e.g., `OrderService.place_order(user, cart, address_data)`).
- **Return Type:** Return domain objects or explicit results (`ServiceResult(success=True, order=...)`).

### 2.4. Query Optimization & Zero N+1 Rule

- **Rule:** Every list or relational query must explicitly declare needed relationships.
- **Guideline:**
  - Use `.select_related()` for `ForeignKey` and `OneToOneField`.
  - Use `.prefetch_related()` for `ManyToManyField` and reverse foreign keys.
  - Use `.only()` or `.defer()` when querying tables with large text/JSON fields that are not rendered on the list view.
  - Never execute ORM queries inside template loop tags.

### 2.5. Concurrency & Transaction Integrity Rule

- **Rule:** Any write operation involving money, orders, or stock inventory must be wrapped in `transaction.atomic()`.
- **Rule:** When modifying product stock during checkout, use row-level locking via `select_for_update()` to prevent race conditions:
  ```python
  with transaction.atomic():
      variant = ProductVariant.objects.select_for_update().get(id=variant_id)
      if variant.stock_quantity < quantity:
          raise InsufficientStockError(...)
      variant.stock_quantity -= quantity
      variant.save()
  ```

---

## 3. Security & Compliance Rules

1. **Zero Hardcoded Secrets:**
   - Database credentials, API keys (Stripe, Razorpay), email credentials, and `SECRET_KEY` must always reside in `.env`.
   - Never commit `.env` to Git. Ensure `.gitignore` explicitly blocks `.env` and `*.sqlite3`.

2. **Strict Webhook Verification:**
   - Webhook endpoints must read raw HTTP request body (`request.body`) and verify provider cryptographic signatures before processing.
   - Webhooks must be idempotent: Check if the transaction ID was already handled before running fulfillment logic.

3. **Input Sanitization & CSRF:**
   - Every `POST`/`PUT`/`DELETE` HTML form must include `{% csrf_token %}`.
   - For AJAX/fetch requests, pass `X-CSRFToken` in headers.
   - Disallow unsafe raw HTML rendering (`|safe`) on user-submitted content (reviews, usernames, notes).

4. **Role & Permission Enforcements:**
   - Protect views with `@login_required`, `@user_passes_test`, or custom mixins (`StaffRequiredMixin`, `VendorRequiredMixin`).

---

## 4. API & Standard Response Format

All AJAX endpoints (Cart modifications, Wishlist toggles, Dynamic filter queries) must return consistent JSON payloads:

```json
{
  "success": true,
  "status_code": 200,
  "message": "Item successfully added to cart.",
  "data": {
    "cart_total": "129.99",
    "cart_count": 3,
    "item": {
      "id": "uuid-here",
      "title": "Wireless Headphones",
      "quantity": 1
    }
  },
  "errors": null
}
```

On failure:

```json
{
  "success": false,
  "status_code": 400,
  "message": "Requested quantity exceeds available stock.",
  "data": null,
  "errors": [{ "field": "quantity", "detail": "Only 2 units remaining." }]
}
```

---

## 5. Coding Style & Quality Guidelines

- **PEP 8 Compliance:** Follow standard Python naming conventions (`snake_case` for functions/variables, `PascalCase` for classes).
- **Type Annotations:** Use Python type hints (`from typing import Optional, List, Dict`) on all service and selector functions.
- **UUIDs for Public Entities:** Use `UUIDField` as primary key or external slug for `Order`, `Payment`, and `Cart` to prevent sequential enumeration attacks.
- **Custom Error Pages:** Provide styled, user-friendly templates for `400.html`, `403.html`, `404.html`, and `500.html`.
