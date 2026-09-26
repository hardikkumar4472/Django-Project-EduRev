"""
WSGI config for edurev_swap project.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edurev_swap.settings')
application = get_wsgi_application()
