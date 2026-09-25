#!/usr/bin/env bash
# Exit immediately if any command fails
set -o errexit

export PYTHONUTF8=1

echo "==> Upgrading pip..."
pip install --upgrade pip

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Collecting static assets..."
python ecom/manage.py collectstatic --noinput

echo "==> Verifying database & applying any pending migrations..."
python ecom/manage.py migrate --noinput

echo "==> Ensuring catalog & account data are present..."
python ecom/manage.py ensure_seed_data

echo "==> Bootstrapping admin user if credentials provided..."
python ecom/manage.py ensure_admin

echo "==> Build complete!"
