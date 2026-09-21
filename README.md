# Cartivo &bull; Next-Generation Modern E-Commerce Platform

> *"Shop Smarter. Live Better."*

Cartivo is an enterprise-grade, modular e-commerce web application engineered with **Django 5.2**, **Tailwind CSS v4 (offline compiled)**, and a **20-domain microservice architecture**. It features a modern luxury consumer storefront paired with an executive dark-themed administrative management suite.

---

## Key Highlights

### 1. Storefront Experience
- **Luxury-Minimalist Design:** Polished typography via Google Fonts ('Poppins'), responsive grid layouts, and high-conversion aesthetic.
- **Sticky Curated Category Sub-Menu:** 14 category icons with hover elevation and active state indicators.
- **Flipkart-Style Multi-Offer Carousel:** Touch-swipe and auto-scrolling promotional banner carousel with pagination indicators.
- **AI Shopping Concierge Widget:** Ambient-glow floating assistant interface with instant suggestions and chat capabilities.
- **Customer Authentication:** Secure member login with 1-click Google OAuth and CSRF-protected credential access.

### 2. Executive Superadmin Management Suite
- **Unified Base Layout (`superadmin_base.html`):** Executive dark palette (`#0B0F19`, `#0F172A`, `#131C2E`, `#1E293B`) with persistent collapsible mini-rail mode and mobile drawer overlay.
- **Quick Command Palette (`Ctrl+K`):** Global modal for instant search and deep navigation across all 20 apps and Django DB admin models.
- **100% Offline Asset Delivery:** Zero external CDN dependencies; Tailwind CSS is pre-compiled locally and Lucide icons are bundled offline in `static/js/lucide.min.js`.
- **Specialized Management Consoles:**
  - **Executive Dashboard (`/management/dashboard/`):** Total orders, sales volume, platform accounts, domain health, and live security audit stream.
  - **Sales & Financial KPIs (`/management/sales/`):** 6 financial metric cards, pure SVG 30-day revenue curve, gateway channel split, and sales transactions ledger.
  - **Graph Analyst & Analytics (`/management/analytics/`):** Storefront views, 5-stage conversion funnel cohort, revenue domain split donut, and regional traffic telemetry.
  - **20-Domain Infrastructure Matrix (`/management/domains/`):** Unified service registry for all 20 Django micro-domain apps, phase badges, category pills, and direct admin DB links.
  - **Platform User Accounts Directory (`/management/users/`):** Central authentication ledger with role pills, active states, and permission controls.
- **Client-Side Table Engine & Print Pipeline (`table-paginator.js`):**
  - Configurable rows-per-page (5, 10, 20, All), windowed page numbers, dynamic info counter, and seamless integration with live search and category filters.
  - Universal `@media print` stylesheet with dedicated "Print List" buttons, automatic un-pagination during print events, repeating headers, and print metadata.

---

## 20 Modular Domain Apps Architecture

The system is decoupled into 20 single-responsibility domain apps located under `apps/`:

| Domain App | Primary Responsibility |
| :--- | :--- |
| `accounts` | Users, authentication, customer profiles, addresses, role permissions |
| `catalog` | Products, hierarchical categories, brands, variants, specifications |
| `inventory` | Stock tracking, warehouses, reservations, concurrency locking |
| `search` | Product queries, multi-attribute facet filtering, analytics |
| `cart` | Dual-cart architecture (guest session + persistent user DB cart) |
| `wishlist` | Customer saved items, private lists, stock alerts |
| `checkout` | Multi-step checkout pipeline, shipping addresses, order review |
| `payments` | Gateway integrations (Stripe, PayPal, Apple Pay, COD), idempotent webhooks |
| `orders` | Order lifecycle state machine, historical snapshots, PDF invoices |
| `shipping` | Carrier integrations, rate calculations, tracking dispatches |
| `fulfillment` | Warehouse picking lists, packing slips, shipment dispatches |
| `promotions` | Discount codes, tiered promotional campaigns, referral vouchers |
| `reviews` | Verified-buyer customer ratings, reviews, moderation queues |
| `notifications` | Transactional email alerts, Celery workers, delivery status updates |
| `recommendations` | Cross-sell, upsell, and personalized shopping suggestions |
| `cms` | Storefront pages, promotional banner carousels, navigational menus |
| `analytics` | Financial reporting, sales funnels, AOV, customer LTV |
| `support` | Customer inquiries, helpdesk tickets, knowledge base FAQs |
| `audit` | Administrative activity logs, security mutation audit trails |
| `settings` | Platform-wide operational configuration and feature flags |

---

## Tech Stack

- **Backend:** Python 3.13, Django 5.2
- **Database:** SQLite (development) / PostgreSQL 16 (production)
- **Styling:** Tailwind CSS v4 via `@tailwindcss/cli` (pre-compiled to `static/src/output.css` & `static/css/output.css`)
- **Typography:** Google Fonts ('Poppins', 'JetBrains Mono')
- **Icons:** Lucide Icons (Offline bundle in `static/js/lucide.min.js`)
- **JavaScript:** Pure Vanilla JavaScript (zero heavy frontend frameworks)

---

## Getting Started

### 1. Prerequisites
- Python 3.12+ (Python 3.13 recommended)
- Node.js 18+ & npm (for Tailwind CSS build)

### 2. Environment Setup & Installation
```bash
# Navigate to the project root
cd d:/django_project/E-Commerce/E-Commerce

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Configure environment variables (.env)
cp .env.example .env

# Install Python dependencies
pip install -r requirements.txt

# Navigate to Django application directory
cd ecom
```

### 3. Database Migrations
```bash
python manage.py migrate
```

### 4. Running the Test Suite
```bash
python manage.py test apps.catalog apps.cart apps.inventory apps.orders apps.wishlist apps.reviews apps.accounts apps.checkout apps.cms apps.core
```

### 5. Compiling Tailwind CSS
```bash
# Compile minified production stylesheets
npm run build

# Or run live watcher during active frontend styling
npm run dev
```

### 6. Running the Local Development Server
```bash
python manage.py runserver
```

Open your browser to:
- **Consumer Storefront:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Customer Login:** [http://127.0.0.1:8000/accounts/login/](http://127.0.0.1:8000/accounts/login/)
- **Management Directory:** [http://127.0.0.1:8000/management/](http://127.0.0.1:8000/management/)
- **Superadmin Executive Console:** [http://127.0.0.1:8000/management/dashboard/](http://127.0.0.1:8000/management/dashboard/)
- **Django Administration:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

> **Development Superuser:** Exactly one primary development superuser exists with username `admin`. Management logins are secured via `UniversalSessionSecurityMiddleware`.

---

## Project Structure

```
E-Commerce/
├── .env.example                # Safe environment variable configuration template
├── architecture.md             # System architecture, ERD, and technical flow
├── design.md                   # UI styleguide, design tokens, and print standards
├── memory.md                   # Session history, decisions, and active file index
├── phases.md                   # 10-phase chronological implementation roadmap
├── prd.md                      # Product requirements document & domain matrix
├── README.md                   # Project overview & documentation
├── rules.md                    # Coding standards, N+1 prevention, and conventions
└── ecom/
    ├── manage.py               # Django CLI utility
    ├── package.json            # Node.js Tailwind compilation scripts
    ├── ecom/                   # Project configuration root
    │   ├── settings.py         # App settings & installed modules
    │   ├── urls.py             # Root URL router
    │   └── wsgi.py             # WSGI entrypoint
    ├── apps/                   # 20 modular domain microservice apps
    │   ├── accounts/
    │   ├── catalog/
    │   ├── core/               # Superadmin views, URLs, and management engines
    │   └── ... (20 apps)
    ├── templates/              # Centralized template hierarchy
    │   ├── base.html           # Storefront master template
    │   ├── components/         # Modular UI partials
    │   └── management/         # Superadmin base & subpage templates
    └── static/
        ├── css/                # Compiled CSS stylesheets
        ├── js/                 # Local Lucide icons & TablePaginator engine
        └── images/             # Cartivo brand marks, favicons, and logos
```

---

## License & Ownership
Copyright &copy; 2026 Cartivo. All rights reserved.
