from django.db import models


class RentalCategory(models.TextChoices):
    """What kind of rental a `RentalListing` is. Kept to two values for this
    basic scaffold - a distinct listing per vehicle/kit is the only "tier"
    concept this vertical needs, unlike Trips' separate TripPackage model."""

    VEHICLE = "VEHICLE", "Vehicle"
    GEAR = "GEAR", "Gear"


class RentalListingStatus(models.TextChoices):
    """Editorial state of a RentalListing, independent of `is_active` (which
    is soft-delete/visibility, not workflow)."""

    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"


class RentalBookingStatus(models.TextChoices):
    """Mirrors django_trips.choices.BookingStatus's lifecycle - a guest,
    out-of-band-payment booking model, not an in-app payment flow."""

    PENDING = "PENDING", "Pending"
    WAITING_PAYMENT = "WAITING_PAYMENT", "Awaiting Payment"
    CONFIRMED = "CONFIRMED", "Confirmed"
    PARTIAL_PAYMENT = "PARTIAL_PAYMENT", "Partial Payment"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"

    @classmethod
    def is_cancelled(cls, status):
        return status == cls.CANCELLED

    @classmethod
    def can_be_cancelled(cls, status):
        return status in (cls.PENDING, cls.WAITING_PAYMENT, cls.CANCELLED)
