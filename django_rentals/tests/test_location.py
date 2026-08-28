"""
P9.4 regression coverage: Location's swappable-model wiring and the
LocationAdapter contract.
"""

from django.test import TestCase, override_settings

from django_rentals.location_adapter import LocationAdapter, get_location_adapter
from django_rentals.models import Location, get_location_model
from django_rentals.tests.factories import LocationFactory


class StubLocationAdapter(LocationAdapter):
    """Importable-by-dotted-path stand-in for testing the
    DJANGO_RENTALS_LOCATION_ADAPTER override - import_string() can't
    resolve a class defined inside a test method's local scope."""


class LocationSwappableTestCase(TestCase):
    def test_location_meta_swappable_setting_name(self):
        self.assertEqual(Location._meta.swappable, "DJANGO_RENTALS_LOCATION_MODEL")

    def test_unswapped_by_default(self):
        self.assertIsNone(Location._meta.swapped)

    def test_get_location_model_returns_location_by_default(self):
        self.assertIs(get_location_model(), Location)


class LocationAdapterTestCase(TestCase):
    def setUp(self):
        self.location = LocationFactory(name="Hunza", lat=36.3167, lng=74.65)
        self.adapter = LocationAdapter()

    def test_get_name(self):
        self.assertEqual(self.adapter.get_name(self.location), "Hunza")

    def test_get_slug_auto_generated_on_save(self):
        self.assertEqual(self.adapter.get_slug(self.location), "hunza")

    def test_get_lat_and_lng(self):
        self.assertEqual(self.adapter.get_lat(self.location), 36.3167)
        self.assertEqual(self.adapter.get_lng(self.location), 74.65)


class GetLocationAdapterTestCase(TestCase):
    def test_defaults_to_location_adapter(self):
        self.assertIsInstance(get_location_adapter(), LocationAdapter)

    def test_honors_django_rentals_location_adapter_override(self):
        with override_settings(
            DJANGO_RENTALS_LOCATION_ADAPTER=(
                "django_rentals.tests.test_location.StubLocationAdapter"
            )
        ):
            adapter = get_location_adapter()

        self.assertIsInstance(adapter, StubLocationAdapter)
