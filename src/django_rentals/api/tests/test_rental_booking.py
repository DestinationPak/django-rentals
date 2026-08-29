"""
Guest rental-booking create/lookup, and authenticated
retrieve/update/cancel.

Mirrors django_hotels' booking IDOR regression coverage
(django_hotels/api/tests/test_hotel_booking.py, P8.3.4): these tests
are written alongside the endpoints, not after (P0.1/P0.5's own
rule), so a future refactor can't silently reopen the same hole - a
booking must never be readable/writable/cancellable by anyone other
than the guest who proves ownership (lookup) or the user who created
it (retrieve/update/cancel).
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from django_rentals.choices import RentalBookingStatus
from django_rentals.models import RentalBooking
from django_rentals.tests.factories import (
    RentalAvailabilityFactory,
    RentalBookingFactory,
    UserFactory,
)


class RentalBookingCreateTestCase(TestCase):
    def test_create_requires_no_auth(self):
        availability = RentalAvailabilityFactory()

        response = APIClient().post(
            reverse("rentals-api:bookings-create"),
            {
                "availability": availability.id,
                "full_name": "Guest Traveller",
                "email": "guest@example.com",
                "phone_number": "+923009999999",
                "start_date": availability.date,
                "end_date": availability.date,
            },
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_create_sets_created_by_for_authenticated_user(self):
        availability = RentalAvailabilityFactory()
        user = UserFactory()
        client = APIClient()
        client.force_authenticate(user)

        response = client.post(
            reverse("rentals-api:bookings-create"),
            {
                "availability": availability.id,
                "full_name": "Logged In Traveller",
                "email": user.email,
                "phone_number": "+923009999998",
                "start_date": availability.date,
                "end_date": availability.date,
            },
        )

        self.assertEqual(response.status_code, 201, response.data)
        booking = RentalBooking.objects.get(number=response.data["number"])
        self.assertEqual(booking.created_by, user)


class RentalBookingLookupTestCase(TestCase):
    def test_lookup_requires_number_and_email(self):
        """The core IDOR regression: a bare number must never resolve a booking."""
        booking = RentalBookingFactory()

        response = APIClient().get(
            reverse("rentals-api:bookings-lookup"), {"number": booking.number}
        )

        self.assertEqual(response.status_code, 400)

    def test_lookup_by_number_and_correct_email_succeeds(self):
        booking = RentalBookingFactory()

        response = APIClient().get(
            reverse("rentals-api:bookings-lookup"),
            {"number": booking.number, "email": booking.email.upper()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["number"], booking.number)

    def test_lookup_by_number_and_wrong_email_fails(self):
        booking = RentalBookingFactory()

        response = APIClient().get(
            reverse("rentals-api:bookings-lookup"),
            {"number": booking.number, "email": "someone-else@example.com"},
        )

        self.assertEqual(response.status_code, 404)


class RentalBookingRetrieveUpdateTestCase(TestCase):
    def test_retrieve_requires_authentication(self):
        booking = RentalBookingFactory()

        response = APIClient().get(
            reverse("rentals-api:booking-detail", kwargs={"number": booking.number})
        )

        self.assertIn(response.status_code, (401, 403))

    def test_retrieve_scoped_to_owner(self):
        owner = UserFactory()
        own_booking = RentalBookingFactory(created_by=owner)
        client = APIClient()
        client.force_authenticate(owner)

        response = client.get(
            reverse(
                "rentals-api:booking-detail", kwargs={"number": own_booking.number}
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["full_name"], own_booking.full_name)

    def test_retrieve_other_users_booking_returns_404(self):
        """A booking must only be readable by the user who created it (IDOR regression)."""
        other_users_booking = RentalBookingFactory(created_by=UserFactory())
        attacker = UserFactory()
        client = APIClient()
        client.force_authenticate(attacker)

        response = client.get(
            reverse(
                "rentals-api:booking-detail",
                kwargs={"number": other_users_booking.number},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_update_scoped_to_owner(self):
        owner = UserFactory()
        own_booking = RentalBookingFactory(created_by=owner)
        client = APIClient()
        client.force_authenticate(owner)

        response = client.put(
            reverse(
                "rentals-api:booking-detail", kwargs={"number": own_booking.number}
            ),
            {
                "availability": own_booking.availability_id,
                "full_name": "Updated Name",
                "email": own_booking.email,
                "phone_number": own_booking.phone_number,
                "start_date": own_booking.start_date,
                "end_date": own_booking.end_date,
            },
        )

        self.assertEqual(response.status_code, 200, response.data)
        own_booking.refresh_from_db()
        self.assertEqual(own_booking.full_name, "Updated Name")

    def test_update_other_users_booking_returns_404(self):
        """A booking must only be writable by the user who created it (IDOR regression)."""
        other_users_booking = RentalBookingFactory(created_by=UserFactory())
        attacker = UserFactory()
        client = APIClient()
        client.force_authenticate(attacker)

        response = client.put(
            reverse(
                "rentals-api:booking-detail",
                kwargs={"number": other_users_booking.number},
            ),
            {
                "availability": other_users_booking.availability_id,
                "full_name": "Hijacked",
                "email": other_users_booking.email,
                "phone_number": other_users_booking.phone_number,
                "start_date": other_users_booking.start_date,
                "end_date": other_users_booking.end_date,
            },
        )

        self.assertEqual(response.status_code, 404)
        other_users_booking.refresh_from_db()
        self.assertNotEqual(other_users_booking.full_name, "Hijacked")


class RentalBookingCancelTestCase(TestCase):
    def test_cancel_transitions_pending_to_cancelled(self):
        owner = UserFactory()
        booking = RentalBookingFactory(created_by=owner)
        client = APIClient()
        client.force_authenticate(owner)

        response = client.post(
            reverse("rentals-api:booking-cancel", kwargs={"number": booking.number})
        )

        self.assertEqual(response.status_code, 200, response.data)
        booking.refresh_from_db()
        self.assertEqual(booking.status, RentalBookingStatus.CANCELLED)

    def test_cancel_already_cancelled_returns_400(self):
        owner = UserFactory()
        booking = RentalBookingFactory(
            created_by=owner, status=RentalBookingStatus.CANCELLED
        )
        client = APIClient()
        client.force_authenticate(owner)

        response = client.post(
            reverse("rentals-api:booking-cancel", kwargs={"number": booking.number})
        )

        self.assertEqual(response.status_code, 400)

    def test_cancel_other_users_booking_returns_404(self):
        """A booking must only be cancellable by the user who created it (IDOR regression)."""
        other_users_booking = RentalBookingFactory(created_by=UserFactory())
        attacker = UserFactory()
        client = APIClient()
        client.force_authenticate(attacker)

        response = client.post(
            reverse(
                "rentals-api:booking-cancel",
                kwargs={"number": other_users_booking.number},
            )
        )

        self.assertEqual(response.status_code, 404)
        other_users_booking.refresh_from_db()
        self.assertNotEqual(other_users_booking.status, RentalBookingStatus.CANCELLED)
