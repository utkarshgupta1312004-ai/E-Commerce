"""
WSGI config for ecom project.

It exposes the WSGI callable as a module-level variable named ``application``.
Also exposes ``app`` for Vercel Serverless Function runtime.
"""

import os
import sys
from pathlib import Path

# Resolve base directories
CURRENT_DIR = Path(__file__).resolve().parent      # ecom/ecom
BASE_DIR = CURRENT_DIR.parent                      # ecom/
APPS_DIR = BASE_DIR / 'apps'

for directory in [BASE_DIR, APPS_DIR]:
    dir_str = str(directory)
    if dir_str not in sys.path:
        sys.path.insert(0, dir_str)

# Ensure 'ecom' package path includes the inner package directory where settings.py lives
try:
    import ecom
    if hasattr(ecom, '__path__'):
        curr_str = str(CURRENT_DIR)
        if curr_str not in list(ecom.__path__):
            ecom.__path__.append(curr_str)
except Exception:
    pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Vercel serverless function entrypoint alias
app = application
