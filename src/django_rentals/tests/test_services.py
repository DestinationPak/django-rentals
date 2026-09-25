from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from django_rentals.choices import RentalBookingStatus
from django_rentals.models import RentalAvailability, RentalBooking
from django_rentals.services import (
    ALREADY_CANCELLED,
    AVAILABILITY_NOT_START_DATE,
    CANNOT_BE_CANCELLED,
    cancel_rental_booking,
    create_rental_booking,
)
from django_rentals.tests.factories import (
    RentalAvailabilityFactory,
    RentalBookingFactory,
    RentalListingFactory,
    UserFactory,
)

START = date(2026, 10, 1)


def make_days(days=3, units=1, listing_price=4000, **kwargs):
    """One availability row per day from START, on one new listing."""
    listing = RentalListingFactory(price_per_day=listing_price)
    return [
        RentalAvailabilityFactory(
            listing=listing, date=START + timedelta(days=offset), units_available=units, **kwargs
        )
        for offset in range(days)
    ]


class CreateRentalBookingTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.guest = {
            "full_name": "Foo Bar",
            "email": "foo@bar.com",
            "phone_number": "+923331234567",
        }

    def book(self, availability, **kwargs):
        dates = {"start_date": START, "end_date": START + timedelta(days=2)}
        return create_rental_booking(availability, **{**self.guest, **dates, **kwargs})

    def units_left(self, rows):
        return list(
            RentalAvailability.objects.filter(pk__in=[row.pk for row in rows])
            .order_by("date")
            .values_list("units_available", flat=True)
        )

    def test_prices_every_day_in_the_range_inclusive(self):
        rows = make_days(price_per_day=None)

        booking = self.book(rows[0])

        self.assertEqual(booking.total_price, 12000)

    def test_a_date_price_overrides_the_listing_price(self):
        rows = make_days(price_per_day=5000)

        booking = self.book(rows[0])

        self.assertEqual(booking.total_price, 15000)

    def test_a_single_day_counts_as_one_day(self):
        rows = make_days(days=1, price_per_day=None)

        booking = self.book(rows[0], end_date=START)

        self.assertEqual(booking.total_price, 4000)

    def test_rejects_a_range_that_ends_before_it_starts(self):
        rows = make_days()

        with self.assertRaisesMessage(ValidationError, "end_date must be on or after start_date."):
            self.book(rows[0], end_date=START - timedelta(days=1))

    def test_records_who_booked(self):
        user = UserFactory()

        booking = self.book(make_days()[0], created_by=user)

        self.assertEqual(booking.created_by, user)

    def test_takes_one_unit_off_every_day_in_the_range(self):
        rows = make_days(days=4, units=2)

        self.book(rows[0])

        self.assertEqual(self.units_left(rows), [1, 1, 1, 2])

    def test_rejects_an_availability_that_is_not_the_start_date(self):
        rows = make_days()

        with self.assertRaises(ValidationError) as ctx:
            self.book(rows[1])

        self.assertEqual(ctx.exception.message_dict, {"availability": [AVAILABILITY_NOT_START_DATE]})

    def test_rejects_a_range_with_a_sold_out_day(self):
        rows = make_days()
        RentalAvailability.objects.filter(pk=rows[1].pk).update(units_available=0)

        with self.assertRaises(ValidationError) as ctx:
            self.book(rows[0])

        self.assertEqual(ctx.exception.message_dict, {"availability": ["Not available on: 2026-10-02."]})
        self.assertEqual(RentalBooking.objects.count(), 0)
        self.assertEqual(self.units_left(rows), [1, 0, 1])

    def test_rejects_a_range_with_a_day_that_has_no_availability(self):
        rows = make_days(days=2)

        with self.assertRaises(ValidationError) as ctx:
            self.book(rows[0])

        self.assertEqual(ctx.exception.message_dict, {"availability": ["Not available on: 2026-10-03."]})

    def test_ignores_other_listings_on_the_same_days(self):
        rows = make_days(days=1)
        make_days(days=3)

        with self.assertRaises(ValidationError):
            self.book(rows[0])

    def test_the_last_unit_can_only_be_booked_once(self):
        rows = make_days()
        self.book(rows[0])

        with self.assertRaises(ValidationError):
            self.book(rows[0])

        self.assertEqual(RentalBooking.objects.count(), 1)


class CancelRentalBookingTestCase(TestCase):
    def test_cancels_and_gives_a_unit_back_on_each_day(self):
        rows = make_days(days=4, units=0)
        booking = RentalBookingFactory(availability=rows[0], start_date=START, end_date=START + timedelta(days=2))

        cancel_rental_booking(booking)

        booking.refresh_from_db()
        self.assertEqual(booking.status, RentalBookingStatus.CANCELLED)
        self.assertEqual(
            list(RentalAvailability.objects.order_by("date").values_list("units_available", flat=True)),
            [1, 1, 1, 0],
        )

    def test_rejects_an_already_cancelled_booking(self):
        rows = make_days(units=0)
        booking = RentalBookingFactory(availability=rows[0], status=RentalBookingStatus.CANCELLED)

        with self.assertRaisesMessage(ValidationError, ALREADY_CANCELLED):
            cancel_rental_booking(booking)

        self.assertFalse(RentalAvailability.objects.filter(units_available__gt=0).exists())

    def test_rejects_a_confirmed_booking(self):
        booking = RentalBookingFactory(status=RentalBookingStatus.CONFIRMED)

        with self.assertRaisesMessage(ValidationError, CANNOT_BE_CANCELLED):
            cancel_rental_booking(booking)
