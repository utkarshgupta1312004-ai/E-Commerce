import os
import sys
from pathlib import Path

# Add project directories to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
ECOM_DIR = ROOT_DIR / 'ecom'
APPS_DIR = ECOM_DIR / 'apps'
INNER_ECOM_DIR = ECOM_DIR / 'ecom'

for directory in [ECOM_DIR, APPS_DIR]:
    dir_str = str(directory)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

# Ensure 'ecom' package path includes the inner package directory where settings.py lives
try:
    import ecom
    if hasattr(ecom, '__path__'):
        curr_str = str(INNER_ECOM_DIR)
        if curr_str not in list(ecom.__path__):
            ecom.__path__.append(curr_str)
except Exception:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
app = application

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
