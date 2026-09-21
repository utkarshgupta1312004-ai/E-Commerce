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

# Vercel Python WSGI serverless callable
app = get_wsgi_application()
