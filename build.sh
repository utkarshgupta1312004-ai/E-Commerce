#!/usr/bin/env bash
# Exit immediately if any command fails
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static assets..."
python ecom/manage.py collectstatic --noinput

echo "==> Running database migrations..."
python ecom/manage.py migrate

echo "==> Bootstrapping admin user if credentials provided..."
python ecom/manage.py ensure_admin

echo "==> Build complete!"
