# Cartivo E-Commerce &bull; Production Deployment Guide

Cartivo is an enterprise-grade Django 5.2 e-commerce platform with a 20-domain modular architecture, luxury consumer storefront, and an executive dark-themed management suite.

---

## 1. Local Development Setup

Follow these steps to run Cartivo locally:

```bash
# Clone the repository
git clone https://github.com/utkarshgupta1312004-ai/E-Commerce.git
cd E-Commerce

# Create and activate virtual environment
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux / macOS:
# python3 -m venv venv
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your local .env file
cp .env.example .env

# Run database migrations
python ecom/manage.py migrate

# (Optional) Seed demo catalog and management departments
python ecom/manage.py loaddata ecom/fixtures/seed_data.json

# Start development server
python ecom/manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## 2. Render Production Deployment

Cartivo is configured for automated build and deployment on **Render** (via Blueprints or standard Web Service).

### Option A: 1-Click Render Blueprint (Recommended)

1. Push your repository to **GitHub**.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** &rarr; **Blueprint**.
4. Connect your **E-Commerce** repository.
5. Render detects [`render.yaml`](./render.yaml) automatically:
   - It will provision a free managed **PostgreSQL Database** (`cartivo-db`).
   - It will provision the Python **Web Service** (`cartivo-ecommerce`).
   - It will automatically link `DATABASE_URL` from PostgreSQL to the web service.
   - It will generate a secure `SECRET_KEY`.
6. Fill in the prompted values:
   - `DJANGO_SUPERUSER_USERNAME`: `admin` (or your preferred username)
   - `DJANGO_SUPERUSER_PASSWORD`: Your secure production password
   - `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API Key for the AI Shopping Concierge
7. Click **Apply**.
8. Render will run `./build.sh` (install packages, collect static files, run migrations, bootstrap admin) and launch Gunicorn.

---

### Option B: Manual Web Service & PostgreSQL Setup

If you prefer setting up services individually on Render:

#### 1. Create PostgreSQL Database
1. In Render, click **New +** &rarr; **PostgreSQL**.
2. Name: `cartivo-db`, Database: `cartivo`, User: `cartivo_user`, Plan: `Free`.
3. Click **Create Database**.
4. Once created, copy the **Internal Database URL** (e.g. `postgres://cartivo_user:...@dpg-...render.com/cartivo`).

#### 2. Create Web Service
1. Click **New +** &rarr; **Web Service**.
2. Connect your GitHub repository.
3. Configure the following:
   - **Name:** `cartivo-ecommerce`
   - **Region:** Same region as your database
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn --chdir ecom ecom.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
   - **Plan:** `Free`
4. Expand **Advanced** and set:
   - **Health Check Path:** `/health/`
5. Add the required **Environment Variables** (see table below).
6. Click **Create Web Service**.

---

## 3. Required Environment Variables

| Variable | Required | Description | Example / Recommended |
| :--- | :---: | :--- | :--- |
| `SECRET_KEY` | **Yes** | Django secret key (50+ random characters) | *(Render auto-generates if using Blueprint)* |
| `DEBUG` | **Yes** | Production debug flag | `False` |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string | `postgresql://user:pass@host:port/dbname` |
| `ALLOWED_HOSTS` | **Yes** | Comma-separated allowed domain hosts | `.onrender.com,localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | **Yes** | Trusted origins for CSRF POST requests | `https://*.onrender.com` |
| `DJANGO_SUPERUSER_USERNAME` | *Optional* | Initial superuser username | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | *Optional* | Initial superuser password | `StrongPass123!` |
| `DJANGO_SUPERUSER_EMAIL` | *Optional* | Initial superuser email | `admin@cartivo.local` |
| `GEMINI_API_KEY` | *Optional* | Google Gemini API key for AI assistant | `AIzaSy...` |
| `GEMINI_MODEL` | *Optional* | Gemini model ID | `gemini-2.5-flash` |
| `GOOGLE_CLIENT_ID` | *Optional* | Google OAuth Client ID | `...apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | *Optional* | Google OAuth Client Secret | `GOCSPX-...` |

---

## 4. Post-Deployment Verification

Once Render reports **Service is live**:

1. **Verify Health Endpoint:**
   - Navigate to `https://<your-service>.onrender.com/health/`
   - Expected JSON response: `{"status": "ok", "service": "cartivo-ecommerce", "environment": "production"}`
2. **Verify Consumer Storefront:**
   - Visit `https://<your-service>.onrender.com/`
   - Confirm luxury storefront loads with styles, navigation icons, and promotional banner.
3. **Verify Admin Console:**
   - Visit `https://<your-service>.onrender.com/admin/` or `https://<your-service>.onrender.com/management/`
   - Log in using your configured `DJANGO_SUPERUSER_USERNAME` and `DJANGO_SUPERUSER_PASSWORD`.
   - Access the Executive Management Dashboard at `/management/dashboard/`.

---

## 5. Media & File Storage on Render

Render's web service filesystem is containerized. For permanent product image uploads in production:
- Add a **Persistent Disk** on Render (mount path: `/opt/render/project/src/ecom/media`) in Service Settings &rarr; Disks.
- Alternatively, configure an S3 bucket or Cloudinary storage provider.
