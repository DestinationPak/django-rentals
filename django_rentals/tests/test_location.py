"""
P9.4 regression coverage: Location's swappable-model wiring, the
LocationAdapter contract, and the city -> location backfill migration.
"""

import importlib

from django.apps import apps as global_apps
from django.test import TestCase, override_settings

from django_rentals.location_adapter import LocationAdapter, get_location_adapter
from django_rentals.models import Location, RentalListing, get_location_model
from django_rentals.tests.factories import LocationFactory, RentalListingFactory

_backfill_migration = importlib.import_module(
    "django_rentals.migrations.0003_backfill_location_from_city"
)
backfill_location = _backfill_migration.backfill_location


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


class BackfillLocationFromCityTestCase(TestCase):
    """
    Exercises the 0003 data migration's backfill function directly - the
    project's pytest settings run with --no-migrations, so the
    RunPython step never executes as part of the normal test suite.
    Using the real (non-historical) app registry is safe here since
    nothing this function touches has changed shape since 0003 was
    written.
    """

    def test_matching_city_strings_share_one_location(self):
        RentalListingFactory(city="Lahore")
        RentalListingFactory(city="Lahore")

        backfill_location(global_apps, None)

        self.assertEqual(Location.objects.filter(slug="lahore").count(), 1)
        location = Location.objects.get(slug="lahore")
        self.assertEqual(
            RentalListing.objects.filter(location=location).count(), 2
        )

    def test_blank_city_left_unmatched(self):
        listing = RentalListingFactory(city="")

        backfill_location(global_apps, None)

        listing.refresh_from_db()
        self.assertIsNone(listing.location)

    def test_null_city_left_unmatched(self):
        listing = RentalListingFactory(city=None)

        backfill_location(global_apps, None)

        listing.refresh_from_db()
        self.assertIsNone(listing.location)

    def test_distinct_cities_get_distinct_locations(self):
        RentalListingFactory(city="Lahore")
        RentalListingFactory(city="Skardu")

        backfill_location(global_apps, None)

        self.assertEqual(
            set(Location.objects.values_list("name", flat=True)),
            {"Lahore", "Skardu"},
        )
