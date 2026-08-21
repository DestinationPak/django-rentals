"""
Test fixtures for django_rentals' models - mirrors
django_hotels/tests/factories.py one vertical over, so consuming
projects (and this package's own tests) build fixtures the same way
regardless of which vertical they're testing.
"""

from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory.django import DjangoModelFactory

from django_rentals.models import RentalAvailability, RentalBooking, RentalListing, RentalOperator

User = get_user_model()

USER_PASSWORD = "pswd"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Faker("email")
    password = factory.PostGenerationMethodCall("set_password", USER_PASSWORD)


class RentalOperatorFactory(DjangoModelFactory):
    class Meta:
        model = RentalOperator

    name = factory.Faker("company")
    description = factory.Faker("text")
    email = factory.Faker("email")
    mobile = factory.Faker("numerify", text="+92##########")
    cancellation_policy = factory.LazyFunction(
        lambda: [{"policy": "Non-refundable", "days": 0}]
    )
    refund_policy = factory.LazyFunction(
        lambda: [{"policy": "Full refund", "days": 7}]
    )
    verified = True


class RentalListingFactory(DjangoModelFactory):
    class Meta:
        model = RentalListing

    name = factory.Faker("company")
    operator = factory.SubFactory(RentalOperatorFactory)
    city = factory.Faker("city")
    description = factory.Faker("text")
    price_per_day = factory.Faker("random_int", min=2000, max=20000)
    created_by = factory.SubFactory(UserFactory)


class RentalAvailabilityFactory(DjangoModelFactory):
    class Meta:
        model = RentalAvailability

    listing = factory.SubFactory(RentalListingFactory)
    date = factory.Sequence(
        lambda n: (timezone.now() + timedelta(days=7 + n)).date()
    )
    units_available = factory.Faker("random_int", min=1, max=10)


class RentalBookingFactory(DjangoModelFactory):
    """
    Leaves `number`/`otp` unset - `RentalBooking.save()`
    auto-generates both, same as `HotelBookingFactory` does for
    `HotelBooking`. Pass `number=` explicitly when a test needs a
    stable, predictable reference to assert against.
    """

    class Meta:
        model = RentalBooking

    availability = factory.SubFactory(RentalAvailabilityFactory)
    full_name = factory.Faker("name")
    email = factory.Faker("email")
    phone_number = factory.Faker("phone_number")
    start_date = factory.LazyAttribute(lambda o: o.availability.date)
    end_date = factory.LazyAttribute(
        lambda o: o.availability.date + timedelta(days=2)
    )
    created_by = factory.SubFactory(UserFactory)
