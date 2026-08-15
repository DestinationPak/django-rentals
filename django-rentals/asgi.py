"""ASGI config for the rentals throwaway dev project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.common')

application = get_asgi_application()
