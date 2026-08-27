"""RentalListingViewSet filtering: category, city, operator."""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from django_rentals.choices import RentalCategory
from django_rentals.tests.factories import (
    LocationFactory,
    RentalListingFactory,
    RentalOperatorFactory,
)


class RentalListingViewSetFilteringTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("rentals-api:listing-list")

    def _listing_ids(self, params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200, response.data)
        return {row["id"] for row in response.data["results"]}

    def test_filters_by_category(self):
        matching = RentalListingFactory(category=RentalCategory.GEAR)
        RentalListingFactory(category=RentalCategory.VEHICLE)

        listing_ids = self._listing_ids({"category": RentalCategory.GEAR})

        self.assertEqual(listing_ids, {matching.id})

    def test_filters_by_city(self):
        matching = RentalListingFactory(location=LocationFactory(name="Hunza"))
        RentalListingFactory(location=LocationFactory(name="Skardu"))

        listing_ids = self._listing_ids({"city": "Hunza"})

        self.assertEqual(listing_ids, {matching.id})

    def test_filters_by_operator(self):
        operator = RentalOperatorFactory()
        matching = RentalListingFactory(operator=operator)
        RentalListingFactory()

        listing_ids = self._listing_ids({"operator": operator.id})

        self.assertEqual(listing_ids, {matching.id})
