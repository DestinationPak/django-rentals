from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import localdate

from django_rentals.admin import REOPEN_NOT_ALLOWED
from django_rentals.choices import RentalBookingStatus
from django_rentals.models import RentalAvailability, RentalBooking
from django_rentals.tests.factories import (
    RentalAvailabilityFactory,
    RentalBookingFactory,
    RentalListingFactory,
    UserFactory,
)

START = localdate() + timedelta(days=30)


def admin_form_data(form):
    """The POST data a browser would send for an unchanged admin form."""
    data = {}
    for name in form.fields:
        bound = form[name]
        value = bound.value()
        widget = bound.field.widget
        if hasattr(widget, "widgets") and hasattr(widget, "decompress"):
            parts = value if isinstance(value, (list, tuple)) else widget.decompress(value)
            for index, part in enumerate(parts):
                data[f"{name}_{index}"] = "" if part is None else part
        elif isinstance(value, bool):
            if value:
                data[name] = "on"
        elif isinstance(value, (list, tuple)):
            data[name] = [str(item) for item in value]
        else:
            data[name] = "" if value is None else value
    return data


class RentalBookingAdminTestCase(TestCase):
    """Cancelling, reopening and deleting a booking in the admin keep units in step."""

    def setUp(self):
        super().setUp()
        self.client.force_login(UserFactory(is_staff=True, is_superuser=True))
        listing = RentalListingFactory()
        self.rows = [
            RentalAvailabilityFactory(listing=listing, date=START + timedelta(days=offset), units_available=0)
            for offset in range(3)
        ]
        self.booking = RentalBookingFactory(
            availability=self.rows[0],
            start_date=START,
            end_date=START + timedelta(days=2),
            status=RentalBookingStatus.CONFIRMED,
        )
        self.change_url = reverse("admin:django_rentals_rentalbooking_change", args=[self.booking.pk])

    def post_status(self, status):
        form = self.client.get(self.change_url).context["adminform"].form
        return self.client.post(self.change_url, {**admin_form_data(form), "status": status})

    def units(self):
        return list(
            RentalAvailability.objects.filter(pk__in=[row.pk for row in self.rows])
            .order_by("date")
            .values_list("units_available", flat=True)
        )

    def test_cancelling_gives_a_unit_back_on_each_day(self):
        response = self.post_status(RentalBookingStatus.CANCELLED)

        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, RentalBookingStatus.CANCELLED)
        self.assertEqual(self.units(), [1, 1, 1])

    def test_saving_without_a_status_change_leaves_units_alone(self):
        self.post_status(RentalBookingStatus.CONFIRMED)

        self.assertEqual(self.units(), [0, 0, 0])

    def test_a_cancelled_booking_cannot_be_reopened(self):
        self.post_status(RentalBookingStatus.CANCELLED)

        response = self.post_status(RentalBookingStatus.PENDING)

        self.assertEqual(response.status_code, 200)
        self.assertIn(REOPEN_NOT_ALLOWED, response.context["adminform"].form.errors["status"])
        self.assertEqual(self.units(), [1, 1, 1])

    def test_dates_and_availability_are_read_only_once_the_booking_exists(self):
        form = self.client.get(self.change_url).context["adminform"].form

        for name in ("availability", "start_date", "end_date"):
            self.assertNotIn(name, form.fields)

    def test_deleting_a_live_booking_gives_the_units_back(self):
        delete_url = reverse("admin:django_rentals_rentalbooking_delete", args=[self.booking.pk])

        self.client.post(delete_url, {"post": "yes"})

        self.assertFalse(RentalBooking.objects.exists())
        self.assertEqual(self.units(), [1, 1, 1])
