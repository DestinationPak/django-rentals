"""
Tests for the public date-range availability search endpoint.

Covers RentalAvailabilityFilter's query params (listing/date_from/
date_to) and the queryset's exclusion rules (sold-out dates, an
unpublished/inactive/unverified-operator listing).
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from django_rentals.choices import RentalListingStatus
from django_rentals.tests.factories import (
    RentalAvailabilityFactory,
    RentalListingFactory,
    RentalOperatorFactory,
)


class RentalAvailabilitySearchTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("rentals-api:availabilities")

    def _results(self, params=None):
        response = self.client.get(self.url, params or {})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def test_lists_availabilities_with_no_filters(self):
        RentalAvailabilityFactory(date=date(2030, 1, 10))
        RentalAvailabilityFactory(date=date(2030, 1, 11))

        self.assertEqual(len(self._results()), 2)

    def test_filters_by_listing_slug(self):
        listing = RentalListingFactory()
        matching = RentalAvailabilityFactory(listing=listing)
        RentalAvailabilityFactory()

        results = self._results({"listing": listing.slug})

        self.assertEqual([row["id"] for row in results], [matching.id])

    def test_filters_by_date_range(self):
        too_early = RentalAvailabilityFactory(date=date(2030, 1, 1))
        in_range = RentalAvailabilityFactory(date=date(2030, 1, 15))
        too_late = RentalAvailabilityFactory(date=date(2030, 2, 1))

        results = self._results({"date_from": "2030-01-10", "date_to": "2030-01-20"})

        ids = {row["id"] for row in results}
        self.assertEqual(ids, {in_range.id})
        self.assertNotIn(too_early.id, ids)
        self.assertNotIn(too_late.id, ids)

    def test_excludes_sold_out_dates(self):
        RentalAvailabilityFactory(units_available=0)

        self.assertEqual(self._results(), [])

    def test_excludes_unpublished_listing(self):
        listing = RentalListingFactory(status=RentalListingStatus.DRAFT)
        RentalAvailabilityFactory(listing=listing)

        self.assertEqual(self._results(), [])

    def test_excludes_inactive_listing(self):
        listing = RentalListingFactory(is_active=False)
        RentalAvailabilityFactory(listing=listing)

        self.assertEqual(self._results(), [])

    def test_excludes_unverified_operator_listing(self):
        operator = RentalOperatorFactory(verified=False)
        listing = RentalListingFactory(operator=operator)
        RentalAvailabilityFactory(listing=listing)

        self.assertEqual(self._results(), [])

    def test_row_shape_nests_listing_slug(self):
        listing = RentalListingFactory(name="Land Cruiser")
        RentalAvailabilityFactory(listing=listing)

        row = self._results()[0]

        self.assertEqual(row["listing"]["name"], "Land Cruiser")
        self.assertEqual(row["listing"]["slug"], listing.slug)
