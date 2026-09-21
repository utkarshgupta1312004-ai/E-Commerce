#!/bin/bash
set -e

echo "==> Building Cartivo E-Commerce for Vercel..."

# Install all Python dependencies
python3 -m pip install -r requirements.txt

# Collect static assets into staticfiles/
python3 ecom/manage.py collectstatic --noinput --clear

# Run database migrations and seed data if external database is connected
if [ -n "$DATABASE_URL" ]; then
    echo "==> External database detected, running migrations..."
    python3 ecom/manage.py migrate --noinput
    echo "==> Populating initial store catalog data..."
    python3 ecom/manage.py loaddata fixtures/seed_data.json || true
fi

echo "==> Cartivo build completed successfully!"
