# Project Context & Session Memory

## Project: Next-Generation Modern E-Commerce Platform
**Last Updated:** September 4, 2026  
**Current Phase:** Phase 1 (Foundation & Architecture Setup)  
**Current Status:** Documentation & Architecture Suite Established; Ready for Code Implementation

---

## 1. Active Working Files Index

| File Path | Role / Content | Current Status |
| :--- | :--- | :--- |
| [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md) | Product Requirements Document: Features, Personas, NFRs, KPIs | Complete & Approved |
| [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md) | System Architecture: High-level flow, ERD, sequence diagrams, state machines | Complete & Approved |
| [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) | Tech stack, approved libraries, coding conventions, zero N+1 rules, security | Complete & Approved |
| [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md) | 10-Phase chronological implementation roadmap and task checklists | Complete & Approved |
| [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) | Design system: Poppins Google Font, Tailwind CSS v4 design tokens, UI specs | Updated |
| [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) | Tech stack: Tailwind CSS v4, Poppins font, zero-inline-CSS directives | Updated |
| [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) | Current working file index, session state, decisions, and immediate next steps | Active |
| [userview/templates/homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) | Modern luxury storefront homepage using pure Tailwind CSS & Poppins | Implemented |
| [userview/static/images/cartivo-horizontal.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-horizontal.png) | Horizontal header brand logo (Cartivo emblem + wordmark) | Active |
| [userview/static/images/cartivo-logo.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-logo.png) | Master full brand logo with tagline ("Shop Smarter. Live Better.") | Active |
| [userview/static/images/cartivo-icon.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-icon.png) | Standalone speed cart emblem | Active |
| [userview/static/images/favicon.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.png) | 192x192 high-resolution PNG favicon | Active |
| [userview/static/images/favicon.ico](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.ico) | Multi-size browser favicon ICO (16px, 32px, 48px, 64px) | Active |
| [userview/static/src/input.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/input.css) | Tailwind CSS v4 input file with `@theme` config (Poppins & brand tokens) | Configured |

| [userview/static/src/output.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/output.css) | Compiled Tailwind CSS production output stylesheet | Built (44KB) |
| [userview/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/urls.py) | Storefront user routes (Home root path routed to `home_view`) | Active |
| [userview/views.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/views.py) | `home_view` rendering `homepage.html` | Active |
| [ecom/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/urls.py) | Root URL routing including `userview.urls` | Active |
| [ecom/settings.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/settings.py) | Project settings with `userview.apps.UserviewConfig` registered in `INSTALLED_APPS` | Active |
| [ecom/package.json](file:///d:/django_project/E-Commerce/E-Commerce/ecom/package.json) | Node package config with `@tailwindcss/cli` and `dev` watch script | Active |

---

## 2. Core Architectural Decisions Locked In

1. **20 Decoupled Modular Domain Apps (`apps/`):**
   - The platform architecture is organized into 20 single-responsibility domain apps: `accounts`, `catalog`, `inventory`, `search`, `cart`, `wishlist`, `checkout`, `payments`, `orders`, `shipping`, `fulfillment`, `promotions`, `reviews`, `notifications`, `recommendations`, `cms`, `analytics`, `support`, `audit`, and `settings`.
   - Templates for each app strictly follow the convention `templates/<app_name>/<template_name>.html`.
2. **Custom User Model First:**
   - Must implement `CustomUser` in `apps/accounts` before running the very first database migration to prevent Django auth migration conflicts.
3. **Modular Service Layer Pattern:**
   - Views will stay thin; business logic (checkout math, cart sync, payments) lives exclusively in `apps/<domain>/services.py`.
   - Complex queries, filters, and aggregations live in `apps/<domain>/selectors.py`.
4. **Dual Cart Architecture:**
   - Guest cart stored in secure session.
   - User cart stored in database (`Cart` & `CartItem` models in `apps/cart`).
   - Unified `CartService.merge_session_cart_to_user()` automatically executed upon login.
5. **Concurrency & Inventory Protection:**
   - Database transactions wrapped in `transaction.atomic()`.
   - Stock deduction protected by row-level locking (`select_for_update()`) in `apps/inventory`.
6. **Design System & Styling:**
   - **Framework:** Tailwind CSS v4 via `@tailwindcss/cli`.
   - **Typography:** Google Fonts `'Poppins'` (`300, 400, 500, 600, 700, 800`).
   - **Directives:** Strictly pure Tailwind utility classes; zero internal `<style>` or inline styling.
   - **Iconography:** Lucide Icons via CDN (`unpkg.com/lucide@latest`).

### 2.1. Master Application & Domain Matrix

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

## 3. Current Workspace Snapshot

- Root folder: `d:\django_project\E-Commerce\E-Commerce\`
- Django project folder: `d:\django_project\E-Commerce\E-Commerce\ecom\`
- Active Apps: `userview` (`ecom/userview/`)
- Active Front-end: Tailwind CSS v4 compiled to `ecom/userview/static/src/output.css`.
- Active Storefront View: `home_view` rendering `homepage.html`.
- Dev Server: Running on `ecom`.

---

## 4. Immediate Next Actionable Steps (Phase 1 Kickoff)

- [ ] **Step 1:** Reorganize `ecom/ecom/settings.py` into a modular package:
  - `ecom/ecom/settings/base.py`
  - `ecom/ecom/settings/development.py`
  - `ecom/ecom/settings/production.py`
- [ ] **Step 2:** Create `.env` and `.env.example` using `django-environ`.
- [ ] **Step 3:** Create `apps/` directory and configure Python path in `manage.py` & `settings/base.py`.
- [ ] **Step 4:** Generate the `apps/accounts` app and define the `CustomUser` model.
- [ ] **Step 5:** Point `AUTH_USER_MODEL = 'accounts.CustomUser'` in settings.
- [ ] **Step 6:** Run initial database migrations (`makemigrations accounts` -> `migrate`).

---

## 5. Working Directives & Protocol
- **Instruction-Driven Execution:** Strictly follow user instructions step-by-step; do not leap ahead unprompted.
- **Specification Compliance:** Align all code, models, views, and templates with [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md), [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md), [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md), [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md), and [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md).
- **Continuous Memory Sync:** Update [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) with active working files, completed steps, and state changes after every instructed modification.

---

## 6. Session Change Log
- **2026-09-04:**
  - Standardized and expanded [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md) with comprehensive feature specifications, user personas, NFRs, and success metrics.
  - Upgraded [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md) with Mermaid ERD, sequence diagrams for search, cart sync, checkout concurrency, and webhook processing.
  - Authored [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) defining libraries, zero N+1 rules, layered service pattern, and security standards.
  - Authored [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md) establishing a 10-phase milestone roadmap.
  - Authored [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) containing the full design token system, typography scale, and UI component specifications.
  - Initialized and updated [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) with working directives and current working file tracking protocol.
  - **Full Codebase Audit Completed:** Read and verified all documents and code files ([prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md), [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md), [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md), [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md), [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md), [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md), `manage.py`, `settings.py`, `urls.py`, `wsgi.py`, `asgi.py`, `.gitignore`, and `README.md`).
  - **Userview App Creation & Wiring:**
    - Created `userview` app inside `ecom/`.
    - Registered `userview.apps.UserviewConfig` in `INSTALLED_APPS` inside [settings.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/settings.py).
    - Defined storefront route in [userview/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/urls.py).
    - Mounted `userview.urls` at root in [ecom/urls.py](file:///d:/django_project/E-Commerce/E-Commerce/ecom/ecom/urls.py).
  - **Brand Identity & Logo Integration:**
    - Integrated uploaded **Cartivo** image ("Shop Smarter. Live Better.").
    - Generated multi-resolution [favicon.ico](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.ico) and [favicon.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/favicon.png) cropped and centered from the shopping cart speed emblem.
    - Generated [cartivo-horizontal.png](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/images/cartivo-horizontal.png) tailored for header and footer navigation.
    - Updated [homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) with favicon links in `<head>`, brand logo in sticky navigation header, and footer brand block.
    - Updated [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) with Brand Identity & Logo Assets section.
  - **Tablet & Mobile Responsiveness + Skeleton Shimmer Animations:**
    - Configured `@keyframes shimmer` and `shimmer-effect` in [input.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/input.css) and recompiled to [output.css](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/static/src/output.css).
    - Updated [homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) with responsive navigation drawer, mobile search, and bottom app bar.
  - **Multi-Offer Interactive Hero Slider:**
    - Implemented a 4-slide carousel in [homepage.html](file:///d:/django_project/E-Commerce/E-Commerce/ecom/userview/templates/homepage.html) with distinct promotional campaigns:
      - **Slide 1:** Autumn / Winter Drop & 20% Off Storewide (`CARTIVO20`) &bull; Studio ANC Pro spotlight.
      - **Slide 2:** Horology Week & Flat $100 Off (`CHRONO100`) &bull; Titanium Smart Chronograph spotlight.
      - **Slide 3:** Sartorial Clearance & Up to 40% Off Outerwear &bull; Atelier Merino Coat spotlight.
      - **Slide 4:** Audio Weekend & Buy 1 Get 50% Off Earbuds &bull; Aura ANC Pro Earbuds spotlight.
  - **Category Sub-Menu Bar Below Navbar:**
    - Inserted directly below `<header>` navigation matching user reference design:
      - 14 distinct category items: For You, Fashion, Mobiles, Electronics, Beauty, Home, Appliances, Toys & Baby, Food & Grocery, Auto Acc., Sports & Fitness, Furniture, Books & Media, 2 Wheelers.
      - Styled matching the visual reference with amber icons, rounded icon cards (`w-10 h-10 rounded-xl`), hover lift, and active blue indicator line under "For You".
      - Fully responsive with zero scrollbars on overflow (`no-scrollbar`).
  - **Flipkart-Style Multi-Banner Promotional Carousel & Large Slider Removal:**
    - Completely removed obsolete full-width `#hero-slider-section` (4 full-screen slides).
    - Directly below Category Sub-Menu, implemented the modern Flipkart-style promotional offer banners carousel matching the user's reference image:
      - Multi-card landscape view (`w-[88vw] sm:w-[500px] md:w-[540px] lg:w-[570px] xl:w-[600px] h-[195px] sm:h-[225px] md:h-[240px] rounded-3xl`) with multi-card peek on desktop and mobile.
      - **Banner 1 (Dark Carbon):** VIRAT V1 5G &bull; From ₹14,499 &bull; Now with 128 GB storage &bull; BIG BACHAT DAYS badge.
      - **Banner 2 (Cyan Grid):** Ortho slippers &bull; Under ₹399 &bull; Comfy picks, going fast! &bull; PNB Up to ₹4,200 Instant Discount bank pill &bull; Framed product showcase.
      - **Banner 3 (Mint Teal):** Best fragrance picks &bull; Min. 50% Off &bull; PARK AVENUE, BEARDO... &bull; PNB bank discount pill &bull; Framed luxury perfume showcase.
      - **Banner 4 (Midnight Indigo):** Studio Wireless ANC &bull; Flat 45% Off &bull; Spatial audio with 40H playtime &bull; HDFC bank cashback pill.
      - **Banner 5 (Warm Sunset):** Smart Chronographs &bull; Under ₹2,999 &bull; Titanium build &bull; No-Cost EMI pill.
      - Centered pagination dots matching the screenshot (`. . . . - . .`) with active pill width expansion (`w-6 sm:w-8 bg-slate-900`).
      - Smooth CSS snap-scroll (`snap-x snap-mandatory`), desktop hover navigation arrows, touch-swipe gestures, and 4.5s autoplay with pause-on-hover/touch.
    - Recompiled Tailwind CSS production output (0 errors, 132ms) and validated zero Django check errors.
    - Updated [design.md](file:///d:/django_project/E-Commerce/E-Commerce/design.md) (Section 5.6) and synchronized [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md).
- **2026-09-05:**
  - Integrated the comprehensive **20-App Modular Domain Architecture** across all specification and planning documents:
    - Updated [prd.md](file:///d:/django_project/E-Commerce/E-Commerce/prd.md) with the Master Domain Architecture Table and detailed capability breakdowns for all 20 apps (`accounts`, `catalog`, `inventory`, `search`, `cart`, `wishlist`, `checkout`, `payments`, `orders`, `shipping`, `fulfillment`, `promotions`, `reviews`, `notifications`, `recommendations`, `cms`, `analytics`, `support`, `audit`, `settings`).
    - Updated [architecture.md](file:///d:/django_project/E-Commerce/E-Commerce/architecture.md) with the directory structure reflecting all 20 apps under `apps/`, template hierarchy (`templates/<app_name>/<template_name>.html`), and the Master Domain Matrix.
    - Updated [phases.md](file:///d:/django_project/E-Commerce/E-Commerce/phases.md) aligning the 10-phase chronological implementation roadmap and checklists directly with the 20 target apps.
    - Updated [rules.md](file:///d:/django_project/E-Commerce/E-Commerce/rules.md) adding the 20 modular apps registry and template directory conventions.
    - Updated [memory.md](file:///d:/django_project/E-Commerce/E-Commerce/memory.md) with core architectural decisions and session tracking.
