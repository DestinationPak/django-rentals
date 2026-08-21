"""
Tests for RentalListingViewSet - the public rental catalog surface.

Mirrors django_hotels' test_hotel_viewset.py-style coverage (P8.3.3):
the router-level read-only guarantee, and that anonymous and
authenticated reads return the identical, unscoped catalog.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from django_rentals.choices import RentalListingStatus
from django_rentals.tests.factories import RentalListingFactory, RentalOperatorFactory, UserFactory


class RentalListingViewSetTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.own_operator = RentalOperatorFactory()
        cls.other_operator = RentalOperatorFactory()
        cls.own_listing = RentalListingFactory(operator=cls.own_operator)
        cls.other_listing = RentalListingFactory(operator=cls.other_operator)
        cls.url = reverse("rentals-api:listing-list")

    def _listing_ids(self, client=None):
        response = (client or APIClient()).get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        return {row["id"] for row in response.data["results"]}

    def test_anonymous_user_sees_the_full_catalog(self):
        listing_ids = self._listing_ids()

        self.assertIn(self.own_listing.id, listing_ids)
        self.assertIn(self.other_listing.id, listing_ids)

    def test_authenticated_user_sees_the_full_catalog_unscoped(self):
        client = APIClient()
        client.force_authenticate(UserFactory())

        listing_ids = self._listing_ids(client)

        self.assertIn(self.own_listing.id, listing_ids)
        self.assertIn(self.other_listing.id, listing_ids)

    def test_write_verbs_not_allowed(self):
        response = APIClient().post(self.url, {"name": "New Listing"})
        self.assertEqual(response.status_code, 405)

    def test_draft_listing_excluded_from_catalog(self):
        draft = RentalListingFactory(
            operator=self.own_operator, status=RentalListingStatus.DRAFT
        )

        listing_ids = self._listing_ids()

        self.assertNotIn(draft.id, listing_ids)

    def test_unverified_operators_listing_excluded_from_catalog(self):
        unverified_operator = RentalOperatorFactory(verified=False)
        listing = RentalListingFactory(operator=unverified_operator)

        listing_ids = self._listing_ids()

        self.assertNotIn(listing.id, listing_ids)
