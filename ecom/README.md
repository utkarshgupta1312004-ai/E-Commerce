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

## Deploying to Vercel (Live Cloud Deployment)

Cartivo is configured for automated, serverless deployment on **Vercel** with `@vercel/python`, `@vercel/static-build`, and **WhiteNoise** static asset delivery.

### 1. One-Click Import from GitHub
1. Log in to [Vercel](https://vercel.com/) and click **"Add New..." > "Project"**.
2. Select and import your GitHub repository: `utkarshgupta1312004-ai/E-Commerce`.
3. **Framework Preset**: Select **Other**.
4. **Root Directory**: Leave as `./` (the root directory contains `vercel.json` and `api/index.py`).

### 2. Configure Environment Variables in Vercel / Production
In your production environment or Vercel Project Settings under **Environment Variables**, add:

| Variable Name | Recommended Value / Description | Required |
| :--- | :--- | :--- |
| `SECRET_KEY` | Generate a strong random key (e.g. 50+ characters) | **Yes** |
| `DEBUG` | `False` in production (`True` for local development in `.env`) | **Yes** |
| `ALLOWED_HOSTS` | `*` or `.vercel.app,.onrender.com,localhost,127.0.0.1` | **Yes** |
| `DATABASE_URL` | PostgreSQL connection URL (e.g. from Neon.tech, Supabase, or Render) | Recommended |
| `GOOGLE_CLIENT_ID` | Google OAuth2 Web Client ID for 1-click Google Sign-In | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth2 Web Client Secret | Optional |
| `GEMINI_API_KEY` | Google Gemini API Key for the AI concierge widget | Optional |
| `RAZORPAY_KEY_ID` | Razorpay Key ID (`rzp_test_...` for test mode, `rzp_live_...` for live) | **Yes** |
| `RAZORPAY_KEY_SECRET` | Razorpay Secret Key (never exposed to frontend/git) | **Yes** |
| `RAZORPAY_CURRENCY` | Base transaction currency (default: `INR`) | Optional |
| `RAZORPAY_WEBHOOK_SECRET` | Secret key configured on Razorpay Dashboard for webhook signatures | **Yes** |

---

## Razorpay Payment Module Integration

Cartivo features a production-grade, secure Razorpay checkout integration with server-side HMAC-SHA256 signature verification, atomic inventory reservation, cart conversion, and idempotent webhook synchronization.

### 1. Payment Architecture & Flow
```
CUSTOMER
   ↓
Shopping Bag (Cart)
   ↓
Checkout Page (/checkout/)
   ↓
Select Payment Method:
   ├── Cash on Delivery (COD) ──→ Order Created (Payment: PENDING, Stock Deducted) ──→ Fulfillment
   └── Razorpay (Online)
           ↓
       1. Frontend posts checkout data to /payments/razorpay/create-order/
       2. Backend strictly recalculates financials & validates stock server-side
       3. Backend creates Razorpay order (amount in paise, currency: INR) via official SDK
       4. Backend returns public razorpay_key_id, razorpay_order_id, and amount
       5. Frontend opens official Razorpay Checkout.js modal (rzp.open())
       6. Customer enters test payment (UPI / Card / NetBanking / Wallet)
       7. Razorpay returns { razorpay_payment_id, razorpay_order_id, razorpay_signature }
       8. Frontend securely POSTs signature payload to /payments/razorpay/verify/
       9. Backend cryptographically verifies HMAC-SHA256 signature
      10. Backend atomically locks row, deducts inventory, creates permanent Order (PAID),
          marks Cart as CONVERTED, and redirects to Order Success & Receipt
```

### 2. Razorpay Dashboard & Test Mode Setup
1. Log in to your [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Toggle the dashboard to **Test Mode** (top-right badge).
3. Navigate to **Account & Settings > API Keys > Generate Key**.
4. Copy the **Key ID** and **Key Secret**.
5. Add them to your local `.env`:
   ```bash
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
   RAZORPAY_CURRENCY=INR
   RAZORPAY_WEBHOOK_SECRET=your_custom_webhook_secret
   ```
6. **Webhook Setup (Optional for local, Required for Production)**:
   - Go to **Account & Settings > Webhooks > Add New Webhook**.
   - **Webhook URL**: `https://your-domain.com/payments/razorpay/webhook/`
   - **Secret**: Enter the exact secret string you set in `RAZORPAY_WEBHOOK_SECRET`.
   - **Active Events**: Check `payment.captured`, `order.paid`, and `payment.failed`.
   - Webhook processing is idempotent: duplicate deliveries acknowledge HTTP 200 without creating duplicate orders.

### 3. Test Payment Process (Razorpay Test Mode)
When testing in browser on `http://localhost:8000/checkout/`:
- **Cards**: Use test card number `4111 1111 1111 1111`, any future expiry (e.g. `12/28`), any CVV (`123`), and any OTP (`123456` or click "Success").
- **UPI**: Enter `success@razorpay` to simulate a successful UPI approval.
- **Net Banking**: Choose any bank (e.g. HDFC, ICICI, SBI) and click "Success" on the mock bank authorization screen.

### 4. Switching to Production (Test Mode to Live Mode)
To transition to real-money processing:
1. Complete Razorpay KYC activation on the Razorpay Dashboard.
2. Switch dashboard toggle to **Live Mode**.
3. Generate **Live API Keys** (`rzp_live_...`).
4. Update environment variables in production host (e.g. Render / Vercel):
   - Replace `RAZORPAY_KEY_ID` with `rzp_live_...`
   - Replace `RAZORPAY_KEY_SECRET` with the live secret
   - Configure live Webhook endpoint and set `RAZORPAY_WEBHOOK_SECRET`
   - Ensure `DEBUG=False` and `SECURE_SSL_REDIRECT=True`
5. **NEVER** commit live keys to Git or document them in source files.

### 5. Troubleshooting: "Razorpay Checkout Not Opening"
If clicking "Pay with Razorpay" does not launch the Razorpay Checkout popup, check the following checklist in order:

| Step | Verification Point | Diagnostic Action & Resolution |
| :--- | :--- | :--- |
| **1** | **API Credentials** | Ensure `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` in `.env` are valid for your active mode (Test Mode keys start with `rzp_test_`). If credentials are invalid, Razorpay returns `BadRequestError: Authentication failed` and the backend returns HTTP 400. |
| **2** | **DEBUG & SSL on Localhost** | In `.env`, ensure `DEBUG=True` is set for local development. If `DEBUG=False`, Django's `SecurityMiddleware` automatically redirects `http://localhost:8000` to `https://localhost:8000`, causing browser fetch errors. |
| **3** | **Checkout.js Loaded** | Ensure `<script src="https://checkout.razorpay.com/v1/checkout.js"></script>` is loaded and not blocked by browser adblockers (Brave Shields, uBlock Origin, Privacy Badger). |
| **4** | **Browser Console Logs** | Open Developer Tools (`F12` > Console) and Network tab. Look at the POST request to `/payments/razorpay/create-order/`. Verify it returns `HTTP 200` with JSON `{ success: true, razorpay_order_id: "order_..." }`. |
| **5** | **Address Validation** | If choosing "Ship to a New Delivery Address", all required fields (Name, Phone, Street, City, State, Postal Code) must be filled. The form validates client-side and backend will reject missing address data with a clear toast. |
| **6** | **Active Cart Items** | Order total must be $> 0$ and active stock must be available in the warehouse. Server recalculates prices and prevents checkout on out-of-stock items. |

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
