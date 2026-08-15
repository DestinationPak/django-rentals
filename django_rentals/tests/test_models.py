import datetime

import pytest
from django.contrib.auth import get_user_model

from django_rentals.models import RentalAvailability, RentalBooking, RentalListing, RentalOperator

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_rental_booking_number_and_otp_are_generated():
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

    assert booking.number.startswith("DPR")
    assert len(booking.otp) == 4


def test_rental_operator_active_manager_filters_unverified():
    RentalOperator.objects.create(name="Unverified Co", verified=False)
    verified = RentalOperator.objects.create(name="Verified Co", verified=True)

    assert list(RentalOperator.objects.active()) == [verified]
