import importlib

from django.test import SimpleTestCase

import django_rentals.api


class ApiDeprecationTestCase(SimpleTestCase):
    def test_importing_the_api_warns_it_is_removed_in_1_0(self):
        with self.assertWarnsRegex(DeprecationWarning, "removed in django-rentals 1.0.0"):
            importlib.reload(django_rentals.api)
