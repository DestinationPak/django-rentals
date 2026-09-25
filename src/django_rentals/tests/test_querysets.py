from datetime import timedelta

from django.test import TestCase
from django.utils.timezone import localdate

from django_rentals.choices import RentalListingStatus
from django_rentals.models import RentalAvailability, RentalBooking, RentalListing
from django_rentals.tests.factories import (
    RentalAvailabilityFactory,
    RentalBookingFactory,
    RentalListingFactory,
)


class PublishedListingsTestCase(TestCase):
    def test_includes_published_active_listings_of_verified_operators(self):
        listing = RentalListingFactory()

        self.assertEqual(list(RentalListing.objects.published()), [listing])

    def test_leaves_out_drafts(self):
        RentalListingFactory(status=RentalListingStatus.DRAFT)

        self.assertFalse(RentalListing.objects.published().exists())

    def test_leaves_out_inactive_listings(self):
        RentalListingFactory(is_active=False)

        self.assertFalse(RentalListing.objects.published().exists())

    def test_leaves_out_listings_of_unverified_operators(self):
        RentalListingFactory(operator__verified=False)

        self.assertFalse(RentalListing.objects.published().exists())


class BookableAvailabilityTestCase(TestCase):
    def test_includes_open_dates_on_published_listings(self):
        availability = RentalAvailabilityFactory(units_available=1)

        self.assertEqual(list(RentalAvailability.objects.bookable()), [availability])

    def test_leaves_out_sold_out_dates(self):
        RentalAvailabilityFactory(units_available=0)

        self.assertFalse(RentalAvailability.objects.bookable().exists())

    def test_leaves_out_past_dates(self):
        RentalAvailabilityFactory(date=localdate() - timedelta(days=1), units_available=2)

        self.assertFalse(RentalAvailability.objects.bookable().exists())

    def test_open_keeps_sold_out_dates(self):
        availability = RentalAvailabilityFactory(units_available=0)

        self.assertEqual(list(RentalAvailability.objects.open()), [availability])

    def test_leaves_out_dates_on_unpublished_listings(self):
        RentalAvailabilityFactory(listing__status=RentalListingStatus.DRAFT)

        self.assertFalse(RentalAvailability.objects.bookable().exists())


class MatchingGuestTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.booking = RentalBookingFactory(email="guest@example.com")

    def test_matches_number_and_email_ignoring_case(self):
        matches = RentalBooking.objects.matching_guest(
            self.booking.number, email="GUEST@example.com"
        )

        self.assertEqual(list(matches), [self.booking])

    def test_never_matches_on_number_alone(self):
        self.assertFalse(RentalBooking.objects.matching_guest(self.booking.number).exists())

    def test_a_wrong_email_matches_nothing(self):
        matches = RentalBooking.objects.matching_guest(
            self.booking.number, email="someone@else.com"
        )

        self.assertFalse(matches.exists())
