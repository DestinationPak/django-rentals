"""
P9.4 regression coverage: Location's swappable-model wiring, the
LocationAdapter contract, and the city -> location backfill migration.
"""

import importlib
import uuid

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from django_rentals.location_adapter import LocationAdapter, get_location_adapter
from django_rentals.models import Location, get_location_model
from django_rentals.tests.factories import LocationFactory, RentalOperatorFactory, UserFactory

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


class BackfillLocationFromCityTestCase(TransactionTestCase):
    """
    Exercises the 0003 data migration's RunPython function against a
    historical RentalListing model, not the live one.

    pytest.ini's own `settings.test` runs migration-free (SQLite,
    `--no-migrations`), but docker-compose.yml sets
    DJANGO_SETTINGS_MODULE=settings.common for the `web` service, and
    pytest-django honors that environment variable over the ini value
    - so this suite actually runs against MySQL, still under
    `--no-migrations`. Getting a faithful pre-0004 RentalListing shape
    means replaying the real migration graph up to 0003 with
    MigrationExecutor/ProjectState (overriding MIGRATION_MODULES back
    to its default, since --no-migrations otherwise hides every app's
    migration files from the loader), then adding a `city` column to
    the live `django_rentals_rentallisting` table with that historical
    field definition. This is a TransactionTestCase, not a TestCase:
    MySQL can't roll back DDL inside a transaction, and TestCase wraps
    every test in one, so schema_editor.add_field() there raises
    TransactionManagementError. TransactionTestCase runs outside a
    wrapping transaction and truncates tables between tests instead, so
    the column survives across this class's tests and tearDownClass
    drops it explicitly, since nothing will roll it back on its own.
    Operator and created_by rows are created through the live
    factories, since those models are unchanged between 0003 and today
    and share the same tables as their historical counterparts;
    RentalListing rows themselves are created through
    HistoricalRentalListing directly (not RentalListingFactory), since
    the live factory/model no longer knows about `city`.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with override_settings(MIGRATION_MODULES={}):
            executor = MigrationExecutor(connection)
            state = executor.loader.project_state(
                ("django_rentals", "0003_backfill_location_from_city")
            )
        cls.HistoricalRentalListing = state.apps.get_model(
            "django_rentals", "RentalListing"
        )
        cls.historical_apps = state.apps
        cls.city_field = cls.HistoricalRentalListing._meta.get_field("city")

        with connection.schema_editor() as editor:
            editor.add_field(cls.HistoricalRentalListing, cls.city_field)

    @classmethod
    def tearDownClass(cls):
        try:
            with connection.schema_editor() as editor:
                editor.remove_field(cls.HistoricalRentalListing, cls.city_field)
        finally:
            super().tearDownClass()

    def make_listing(self, city):
        operator = RentalOperatorFactory()
        user = UserFactory()
        return self.HistoricalRentalListing.objects.create(
            name="Test Listing",
            slug=uuid.uuid4().hex,
            operator_id=operator.pk,
            created_by_id=user.pk,
            city=city,
        )

    def run_backfill(self):
        backfill_location(self.historical_apps, None)

    def test_matching_city_strings_share_one_location(self):
        self.make_listing(city="Lahore")
        self.make_listing(city="Lahore")

        self.run_backfill()

        self.assertEqual(Location.objects.filter(slug="lahore").count(), 1)
        location = Location.objects.get(slug="lahore")
        self.assertEqual(
            self.HistoricalRentalListing.objects.filter(location_id=location.pk).count(),
            2,
        )

    def test_blank_city_left_unmatched(self):
        listing = self.make_listing(city="")

        self.run_backfill()

        listing.refresh_from_db()
        self.assertIsNone(listing.location_id)

    def test_null_city_left_unmatched(self):
        listing = self.make_listing(city=None)

        self.run_backfill()

        listing.refresh_from_db()
        self.assertIsNone(listing.location_id)

    def test_distinct_cities_get_distinct_locations(self):
        self.make_listing(city="Lahore")
        self.make_listing(city="Skardu")

        self.run_backfill()

        self.assertEqual(
            set(Location.objects.values_list("name", flat=True)),
            {"Lahore", "Skardu"},
        )
