from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase

from django_rentals.services import create_rental_booking
from django_rentals.tests.factories import RentalAvailabilityFactory, UserFactory


class CreateRentalBookingTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.guest = {
            "full_name": "Foo Bar",
            "email": "foo@bar.com",
            "phone_number": "+923331234567",
        }

    def book(self, availability, **kwargs):
        dates = {"start_date": date(2026, 10, 1), "end_date": date(2026, 10, 3)}
        return create_rental_booking(availability, **{**self.guest, **dates, **kwargs})

    def test_prices_every_day_in_the_range_inclusive(self):
        availability = RentalAvailabilityFactory(listing__price_per_day=4000, price_per_day=None)

        booking = self.book(availability)

        self.assertEqual(booking.total_price, 12000)

    def test_a_date_price_overrides_the_listing_price(self):
        availability = RentalAvailabilityFactory(listing__price_per_day=4000, price_per_day=5000)

        booking = self.book(availability)

        self.assertEqual(booking.total_price, 15000)

    def test_a_single_day_counts_as_one_day(self):
        availability = RentalAvailabilityFactory(listing__price_per_day=4000, price_per_day=None)

        booking = self.book(availability, end_date=date(2026, 10, 1))

        self.assertEqual(booking.total_price, 4000)

    def test_rejects_a_range_that_ends_before_it_starts(self):
        with self.assertRaisesMessage(ValidationError, "end_date must be on or after start_date."):
            self.book(RentalAvailabilityFactory(), end_date=date(2026, 9, 30))

    def test_records_who_booked(self):
        user = UserFactory()

        booking = self.book(RentalAvailabilityFactory(), created_by=user)

        self.assertEqual(booking.created_by, user)
