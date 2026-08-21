import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from django_rentals.choices import RentalBookingStatus
from django_rentals.models import RentalAvailability, RentalBooking, RentalListing, RentalOperator

User = get_user_model()


class RentalBookingTestCase(TestCase):
    def test_number_and_otp_are_generated(self):
        user = User.objects.create(username="tester")
        operator = RentalOperator.objects.create(name="Test Operator", verified=True)
        listing = RentalListing.objects.create(
            name="Test Jeep", operator=operator, price_per_day=100, created_by=user
        )
        availability = RentalAvailability.objects.create(
            listing=listing, date=datetime.date.today(), units_available=1
        )
        booking = RentalBooking.objects.create(
            availability=availability,
            full_name="Jane Doe",
            email="jane@example.com",
            phone_number="+10000000000",
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
        )

        self.assertTrue(booking.number.startswith("DPR"))
        self.assertEqual(len(booking.otp), 4)

    def test_cancel_transitions_to_cancelled(self):
        operator = RentalOperator.objects.create(name="Test Operator", verified=True)
        listing = RentalListing.objects.create(
            name="Test Jeep",
            operator=operator,
            price_per_day=100,
            created_by=User.objects.create(username="tester2"),
        )
        availability = RentalAvailability.objects.create(
            listing=listing, date=datetime.date.today(), units_available=1
        )
        booking = RentalBooking.objects.create(
            availability=availability,
            full_name="Jane Doe",
            email="jane@example.com",
            phone_number="+10000000000",
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=2),
        )

        booking.cancel()

        booking.refresh_from_db()
        self.assertEqual(booking.status, RentalBookingStatus.CANCELLED)


class RentalOperatorManagerTestCase(TestCase):
    def test_active_manager_filters_unverified(self):
        RentalOperator.objects.create(name="Unverified Co", verified=False)
        verified = RentalOperator.objects.create(name="Verified Co", verified=True)

        self.assertEqual(list(RentalOperator.objects.active()), [verified])
