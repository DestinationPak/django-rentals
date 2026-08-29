"""
Coverage for AbstractLocation - the base class Location itself now
extends, and that an installer can extend to build a custom Location
model without writing a LocationAdapter.
"""

from django.test import TestCase
from django.test.utils import isolate_apps

from django_rentals.models import AbstractLocation, Location


class AbstractLocationTestCase(TestCase):
    def test_abstract_location_is_abstract(self):
        self.assertTrue(AbstractLocation._meta.abstract)

    def test_location_inherits_abstract_location(self):
        self.assertTrue(issubclass(Location, AbstractLocation))

    def test_location_is_still_concrete_and_swappable(self):
        self.assertFalse(Location._meta.abstract)
        self.assertEqual(Location._meta.swappable, "DJANGO_RENTALS_LOCATION_MODEL")

    def test_default_location_still_slugifies_on_save(self):
        location = Location.objects.create(name="Hunza Valley")

        self.assertEqual(location.slug, "hunza-valley")

    @isolate_apps("django_rentals")
    def test_custom_subclass_gets_fields_and_methods_for_free(self):
        class CustomLocation(AbstractLocation):
            class Meta:
                app_label = "django_rentals"

        instance = CustomLocation(name="Skardu")

        self.assertEqual(str(instance), "Skardu")

    @isolate_apps("django_rentals")
    def test_custom_subclass_can_override_a_single_method(self):
        class CustomLocation(AbstractLocation):
            class Meta:
                app_label = "django_rentals"

            def get_coordinates(self):
                return self.lat, self.lng

        instance = CustomLocation(name="Skardu", lat=35.3, lng=75.6)

        self.assertEqual(instance.get_coordinates(), (35.3, 75.6))
