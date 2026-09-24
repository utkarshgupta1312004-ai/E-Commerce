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

_django_app = get_wsgi_application()

def app(environ, start_response):
    path_info = environ.get('PATH_INFO', '')
    real_path = (
        environ.get('HTTP_X_MATCHED_PATH')
        or environ.get('HTTP_X_FORWARDED_URI')
        or environ.get('RAW_URI')
        or environ.get('REQUEST_URI')
    )
    if real_path and real_path not in ('/api/index.py', '/api/index', '/api', '/ecom/ecom/wsgi.py', '/ecom/wsgi.py'):
        if '?' in real_path:
            real_path = real_path.split('?', 1)[0]
        if not real_path.startswith('/'):
            real_path = '/' + real_path
        environ['PATH_INFO'] = real_path
    elif path_info in ('/api/index.py', '/api/index', '/api', '/ecom/ecom/wsgi.py', '/ecom/wsgi.py'):
        environ['PATH_INFO'] = '/'
    elif path_info.startswith('/api/index.py/'):
        environ['PATH_INFO'] = path_info[len('/api/index.py'):]
    
    return _django_app(environ, start_response)

# Vercel and standard WSGI aliases
application = app
