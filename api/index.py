import os
import sys
from pathlib import Path

# Add project directories to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
ECOM_DIR = ROOT_DIR / 'ecom'

if str(ECOM_DIR) not in sys.path:
    sys.path.insert(0, str(ECOM_DIR))
if str(ECOM_DIR / 'apps') not in sys.path:
    sys.path.insert(0, str(ECOM_DIR / 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')

from django.core.wsgi import get_wsgi_application
app = get_wsgi_application()

# Serverless Database Readiness Guard
try:
    from django.db import connection
    from django.core.management import call_command
    existing_tables = connection.introspection.table_names()
    if 'cms_promobanner' not in existing_tables:
        call_command('migrate', interactive=False)
        seed_fixture = ROOT_DIR / 'fixtures' / 'seed_data.json'
        if seed_fixture.exists():
            try:
                call_command('loaddata', str(seed_fixture))
            except Exception:
                pass
except Exception as e:
    print("Database readiness guard warning:", e)
