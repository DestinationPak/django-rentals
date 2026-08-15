# pylint:disable=all
"""WSGI config for the rentals throwaway dev project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.common")

application = get_wsgi_application()
