"""Business rules for rental bookings, independent of any API layer."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from django_rentals.choices import RentalBookingStatus
from django_rentals.models import RentalAvailability, RentalBooking

DATES_OUT_OF_ORDER = "end_date must be on or after start_date."
AVAILABILITY_NOT_START_DATE = "The availability must be for start_date."
NOT_AVAILABLE_ON = "Not available on: {dates}."
ALREADY_CANCELLED = "Booking is already cancelled."
CANNOT_BE_CANCELLED = "Booking cannot be cancelled."


def validate_rental_dates(start_date, end_date):
    """Raise a ValidationError when the range ends before it starts."""
    if end_date < start_date:
        raise ValidationError(DATES_OUT_OF_ORDER)


def _days(start_date, end_date):
    return [
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    ]


def _first_row_per_day(rows):
    by_day = {}
    for row in rows:
        by_day.setdefault(row.date, row)
    return by_day


def create_rental_booking(  # pylint:disable=too-many-arguments
    availability,
    *,
    full_name,
    email,
    phone_number,
    start_date,
    end_date,
    message=None,
    created_by=None,
):
    """
    Book a listing from `start_date` to `end_date`, both days included.

    `availability` is the listing's row for `start_date`. Every day in the
    range needs an availability row with a unit left, and each of those
    rows gives up one unit. The rows are locked while this happens, so two
    bookings can't both take the last unit on a day. Raises a
    ValidationError, keyed by `availability` for the day checks. Prices the
    booking at `availability`'s per-day price times the number of days.
    """
    validate_rental_dates(start_date, end_date)
    if availability.date != start_date:
        raise ValidationError({"availability": AVAILABILITY_NOT_START_DATE})
    days = _days(start_date, end_date)

    with transaction.atomic():
        taken = _first_row_per_day(
            RentalAvailability.objects.select_for_update()
            .filter(
                listing_id=availability.listing_id,
                date__range=(start_date, end_date),
                units_available__gte=1,
            )
            .order_by("date", "pk")
        )
        missing = [day for day in days if day not in taken]
        if missing:
            dates = ", ".join(day.isoformat() for day in missing)
            raise ValidationError(
                {"availability": NOT_AVAILABLE_ON.format(dates=dates)}
            )

        booking = RentalBooking.objects.create(
            availability=availability,
            full_name=full_name,
            email=email,
            phone_number=phone_number,
            start_date=start_date,
            end_date=end_date,
            message=message,
            created_by=created_by,
            total_price=availability.effective_price_per_day * len(days),
        )
        RentalAvailability.objects.filter(
            pk__in=[row.pk for row in taken.values()]
        ).update(units_available=F("units_available") - 1)

    return booking


def cancel_rental_booking(booking):
    """
    Cancel `booking` and give one unit back on each day it covered.

    Raises a ValidationError when the booking is already cancelled or its
    status no longer allows cancelling.
    """
    if RentalBookingStatus.is_cancelled(booking.status):
        raise ValidationError(ALREADY_CANCELLED)
    if not booking.can_be_cancelled():
        raise ValidationError(CANNOT_BE_CANCELLED)

    with transaction.atomic():
        booking.cancel()
        released = _first_row_per_day(
            RentalAvailability.objects.select_for_update()
            .filter(
                listing_id=booking.availability.listing_id,
                date__range=(booking.start_date, booking.end_date),
            )
            .order_by("date", "pk")
        )
        RentalAvailability.objects.filter(
            pk__in=[row.pk for row in released.values()]
        ).update(units_available=F("units_available") + 1)

    return booking
