# Phase-Wise Project Implementation Roadmap

## Project: Cartivo &bull; Next-Generation Modern E-Commerce Platform

---

## 1. Roadmap & 20 Modular Domain Apps Mapping

```
[ Phase 1: Foundation, Environment & Core Identity ]  ──► apps/accounts, apps/settings, apps/audit, core
                        │
                        ▼
[ Phase 2: Product Catalog & Taxonomy Engine ]        ──► apps/catalog
                        │
                        ▼
[ Phase 3: Inventory Control & Warehousing ]          ──► apps/inventory
                        │
                        ▼
[ Phase 4: Search Engine, Discovery & CMS ]           ──► apps/search, apps/cms
                        │
                        ▼
[ Phase 5: Authentication, Profiles & Wishlist ]      ──► apps/accounts, apps/wishlist
                        │
                        ▼
[ Phase 6: Cart Engine & Promotions/Coupons ]         ──► apps/cart, apps/promotions
                        │
                        ▼
[ Phase 7: Checkout & Multi-Gateway Payments ]        ──► apps/checkout, apps/payments
                        │
                        ▼
[ Phase 8: Orders, Shipping, Fulfillment & Notify ]   ──► apps/orders, apps/shipping, apps/fulfillment, apps/notifications
                        │
                        ▼
[ Phase 9: Reviews, Ratings & Recommendations ]       ──► apps/reviews, apps/recommendations
                        │
                        ▼
[ Phase 10: Operations, Support, Analytics & Launch ] ──► apps/analytics, apps/support, apps/audit, apps/settings
```

### 1.1. Master Domain Mapping Reference

| App Name | Contains Data Of | Dashboard Shows | Templates |
| :--- | :--- | :--- | :--- |
| `accounts` | Users, profiles, addresses, roles | Total users, active users, new users, blocked users | `login`, `register`, `profile`, `users`, `user_detail` |
| `catalog` | Products, categories, brands, attributes, variants | Total products, categories, active products, out-of-stock products | `products`, `product_detail`, `categories`, `brands`, `variants` |
| `inventory` | Stock, warehouses, stock movements | Total stock, low stock, out of stock, reserved stock | `inventory`, `stock_detail`, `warehouses`, `stock_movements` |
| `search` | Search queries, filters, search results | Popular searches, zero-result searches, search trends | `search`, `search_results`, `search_analytics` |
| `cart` | Carts, cart items, abandoned carts | Active carts, abandoned carts, cart value, cart conversion | `cart`, `cart_detail`, `abandoned_carts` |
| `wishlist` | Wishlists, wishlist items | Total wishlists, popular products, wishlist conversions | `wishlist`, `wishlist_detail` |
| `checkout` | Checkout sessions, addresses, shipping selections | Active checkouts, completed checkouts, abandoned checkouts | `checkout`, `address`, `shipping`, `review` |
| `payments` | Transactions, payment methods, refunds | Successful payments, failed payments, pending payments, refunds | `payments`, `transaction_detail`, `refunds` |
| `orders` | Orders, order items, order status, order history | Total orders, pending, processing, shipped, delivered, cancelled | `orders`, `order_detail`, `order_invoice` |
| `shipping` | Shipments, carriers, tracking, shipping zones | Pending shipments, shipped, in-transit, delivered, delayed | `shipments`, `shipment_detail`, `tracking`, `carriers` |
| `fulfillment` | Picking, packing, fulfillment tasks | Pending fulfillment, picking, packing, ready to ship | `fulfillment`, `picking`, `packing`, `tasks` |
| `promotions` | Coupons, discounts, campaigns | Active offers, coupon usage, discount amount, campaign revenue | `promotions`, `coupons`, `campaigns`, `promotion_detail` |
| `reviews` | Reviews, ratings, moderation | Total reviews, average rating, pending/reported reviews | `reviews`, `review_detail`, `moderation` |
| `notifications` | Email, SMS, push notifications, templates | Sent, delivered, failed, opened notifications | `notifications`, `templates`, `notification_detail` |
| `recommendations` | Product recommendations, recommendation rules | Recommendation clicks, CTR, attributed revenue | `recommendations`, `rules`, `recommendation_analytics` |
| `cms` | Pages, banners, menus, content blocks | Published pages, banners, drafts, scheduled content | `pages`, `page_editor`, `banners`, `menus` |
| `analytics` | Sales, customers, products, conversion metrics | Revenue, sales, conversion, AOV, customer analytics | `dashboard`, `sales`, `customers`, `products`, `reports` |
| `support` | Tickets, customer queries, complaints | Open tickets, pending, resolved, response time | `tickets`, `ticket_detail`, `customers`, `knowledge_base` |
| `audit` | Admin actions, login activity, system events | Recent activities, security events, admin actions | `logs`, `activity_detail`, `security_events` |
| `settings` | Store settings, payment settings, shipping settings | Store configuration status | `settings`, `general`, `payment`, `shipping`, `email` |

---

## Phase 1: Foundation, Environment Setup & Core Architecture
- **Target Apps:** `apps/accounts`, `apps/settings`, `apps/audit`, `apps/core`
- [ ] **1.1. Directory Structuring & Settings Package:**
  - Create `apps/` directory and configure `sys.path` in `manage.py` and `settings/`.
  - Split settings into `base.py`, `development.py`, and `production.py`.
  - Integrate `django-environ` with template `.env.example`.
- [ ] **1.2. Custom User Model & Audit Trail (`apps/accounts`, `apps/audit`):**
  - Implement `CustomUser` inheriting from `AbstractBaseUser` and `PermissionsMixin`.
  - Email as `USERNAME_FIELD`, phone number, avatar, role (`customer`, `vendor`, `staff`, `admin`).
  - Set `AUTH_USER_MODEL = 'accounts.CustomUser'` and create initial migration.
  - Setup base audit logging models for user logins and critical mutations.
- [ ] **1.3. Global Store Settings (`apps/settings`):**
  - Store metadata, currency, maintenance mode, and notification configurations.
  - Templates: `settings.html`, `general.html`, `payment.html`, `shipping.html`, `email.html`.

---

## Phase 2: Product Catalog & Taxonomy Engine (`apps/catalog`)
- **Target App:** `apps/catalog`
- [ ] **2.1. Category & Brand Models:**
  - `Category` with self-referencing `parent` for hierarchical trees, slug, icon, and banner.
  - `Brand` with logo, slug, and description.
- [ ] **2.2. Product, Variant & Attribute Models:**
  - `Product`: Title, slug, description, category (FK), brand (FK), base price, is_featured, is_active.
  - `ProductVariant`: SKU, variant name, barcode, price override, attribute JSON.
  - `ProductImage`: Image file, alt text, is_primary, ordering with automated WebP conversion.
- [ ] **2.3. Catalog Templates & Admin Integration:**
  - Inlines for `ProductVariant` and `ProductImage` inside `ProductAdmin`.
  - Templates: `products.html`, `product_detail.html`, `categories.html`, `brands.html`, `variants.html`.

---

## Phase 3: Inventory Control & Warehousing (`apps/inventory`)
- **Target App:** `apps/inventory`
- [ ] **3.1. Warehouse & Stock Models:**
  - `Warehouse`: Name, code, address, is_active.
  - `Stock`: Variant (FK), warehouse (FK), quantity, reserved_quantity, low_stock_threshold.
  - `StockMovement`: Tracking ins/outs, order deductions, returns, manual adjustments.
- [ ] **3.2. Concurrency & Row-Level Locking:**
  - Implement `InventoryService.reserve_stock()` using `select_for_update()` to prevent overselling.
- [ ] **3.3. Inventory Dashboard & Templates:**
  - Stock alerts, warehouse overview, stock movement history.
  - Templates: `inventory.html`, `stock_detail.html`, `warehouses.html`, `stock_movements.html`.

---

## Phase 4: Search Engine, Discovery & Content Management (`apps/search`, `apps/cms`)
- **Target Apps:** `apps/search`, `apps/cms`
- [ ] **4.1. Search Engine & Faceting (`apps/search`):**
  - Full-text search on product titles, categories, brands, tags.
  - Multi-faceted filtering (category tree, price slider, brand checkboxes, in-stock toggle).
  - Search query telemetry: Logging queries, popular searches, zero-result search analytics.
  - Templates: `search.html`, `search_results.html`, `search_analytics.html`.
- [ ] **4.2. Content Management & Banners (`apps/cms`):**
  - Content pages (About, Terms, Privacy), rich page editor.
  - Promotional offer banners (Flipkart-style carousel data source), menu manager.
  - Templates: `pages.html`, `page_editor.html`, `banners.html`, `menus.html`.

---

## Phase 5: Authentication, Profiles & Wishlist (`apps/accounts`, `apps/wishlist`)
- **Target Apps:** `apps/accounts`, `apps/wishlist`
- [ ] **5.1. Authentication Views & Flow (`apps/accounts`):**
  - Customer registration with email verification token.
  - Login view with "Remember Me" session duration support.
  - Password reset flow with secure tokenized link.
  - Customer profile and Address Book (multiple shipping/billing addresses).
  - Templates: `login.html`, `register.html`, `profile.html`, `users.html`, `user_detail.html`.
- [ ] **5.2. Wishlist System (`apps/wishlist`):**
  - `Wishlist` & `WishlistItem` models linked to user and product/variant.
  - AJAX toggle endpoint for live heart icon state update.
  - Dedicated wishlist view with "Move to Cart" one-click action.
  - Templates: `wishlist.html`, `wishlist_detail.html`.

---

## Phase 6: Cart Engine & Promotions/Coupons (`apps/cart`, `apps/promotions`)
- **Target Apps:** `apps/cart`, `apps/promotions`
- [ ] **6.1. Dual-State Cart (`apps/cart`):**
  - Session Cart class for unauthenticated guests.
  - `Cart` and `CartItem` models for authenticated customers.
  - `CartService.merge_session_cart_to_user()` triggered upon login.
  - Abandoned cart snapshot service for recovery campaigns.
  - Templates: `cart.html`, `cart_detail.html`, `abandoned_carts.html`.
- [ ] **6.2. Promotions & Coupon Engine (`apps/promotions`):**
  - `Coupon` model: Code, discount type (percentage/fixed), discount value, expiry, min spend, max uses.
  - Validation service verifying eligibility, dates, and per-user redemption limits.
  - Instant discount calculation and applied coupon badge on cart/checkout.
  - Templates: `promotions.html`, `coupons.html`, `campaigns.html`, `promotion_detail.html`.

---

## Phase 7: Checkout & Multi-Gateway Payments (`apps/checkout`, `apps/payments`)
- **Target Apps:** `apps/checkout`, `apps/payments`
- [ ] **7.1. Multi-Step Checkout Flow (`apps/checkout`):**
  - Step 1: Address selection & quick-add form.
  - Step 2: Shipping method selection with cost computation.
  - Step 3: Payment method choice (Stripe, Razorpay, Cash on Delivery).
  - Step 4: Final review with grand total breakdown.
  - Templates: `checkout.html`, `address.html`, `shipping.html`, `review.html`.
- [ ] **7.2. Payment Gateways & Webhooks (`apps/payments`):**
  - Stripe Payment Intent + Elements frontend mounting.
  - Razorpay Order creation + Checkout SDK integration.
  - Cryptographically signed, idempotent webhook listeners (`request.body` signature verification).
  - Automated refund handler.
  - Templates: `payments.html`, `transaction_detail.html`, `refunds.html`.

---

## Phase 8: Orders, Shipping, Fulfillment & Notifications (`apps/orders`, `apps/shipping`, `apps/fulfillment`, `apps/notifications`)
- **Target Apps:** `apps/orders`, `apps/shipping`, `apps/fulfillment`, `apps/notifications`
- [ ] **8.1. Order Management (`apps/orders`):**
  - State machine: `PENDING_PAYMENT` → `PROCESSING` → `SHIPPED` → `DELIVERED` → `CANCELLED`.
  - Immutable OrderItem snapshots (title, SKU, price).
  - Branded PDF invoice generation via `ReportLab`.
  - Templates: `orders.html`, `order_detail.html`, `order_invoice.html`.
- [ ] **8.2. Shipping & Carrier Tracking (`apps/shipping`):**
  - Shipments, tracking number assignment, shipping zones and rate tables.
  - Templates: `shipments.html`, `shipment_detail.html`, `tracking.html`, `carriers.html`.
- [ ] **8.3. Warehouse Fulfillment Operations (`apps/fulfillment`):**
  - Pick-lists, packing slips, dispatch handoff, fulfillment status tracking.
  - Templates: `fulfillment.html`, `picking.html`, `packing.html`, `tasks.html`.
- [ ] **8.4. Asynchronous Notifications (`apps/notifications`):**
  - Celery background workers for order confirmation, shipping updates, invoice dispatch.
  - Templates: `notifications.html`, `templates.html`, `notification_detail.html`.

---

## Phase 9: Reviews, Ratings & Recommendations (`apps/reviews`, `apps/recommendations`)
- **Target Apps:** `apps/reviews`, `apps/recommendations`
- [ ] **9.1. Verified Buyer Reviews (`apps/reviews`):**
  - Review submission gated strictly to verified purchasers with delivered orders.
  - 1-to-5 star rating breakdown, review photo attachments, moderation queue.
  - Templates: `reviews.html`, `review_detail.html`, `moderation.html`.
- [ ] **9.2. Personalization & Upselling (`apps/recommendations`):**
  - "Frequently Bought Together" bundles, "Related Products" rules.
  - Telemetry: Click-through tracking and revenue attribution.
  - Templates: `recommendations.html`, `rules.html`, `recommendation_analytics.html`.

---

## Phase 10: Store Operations, Support, Analytics & Launch (`apps/analytics`, `apps/support`, `apps/audit`, `apps/settings`)
- **Target Apps:** `apps/analytics`, `apps/support`, `apps/audit`, `apps/settings`
- [ ] **10.1. Analytics & Business Intelligence (`apps/analytics`):**
  - Executive KPI tiles: Revenue, Sales, Conversion rate, AOV.
  - Interactive charts and exportable reports.
  - Templates: `dashboard.html`, `sales.html`, `customers.html`, `products.html`, `reports.html`.
- [ ] **10.2. Customer Support & Helpdesk (`apps/support`):**
  - Ticketing system, inquiry routing, FAQ knowledge base.
  - Templates: `tickets.html`, `ticket_detail.html`, `customers.html`, `knowledge_base.html`.
- [ ] **10.3. Audit Logs & System Activity (`apps/audit`):**
  - Administrative activity logs, security exception monitoring.
  - Templates: `logs.html`, `activity_detail.html`, `security_events.html`.
- [ ] **10.4. Performance, Security & Launch Hardening:**
  - Redis cache integration, zero N+1 query audit, rate limiting.
  - Dynamic `sitemap.xml`, `robots.txt`, and production deployment configurations.

