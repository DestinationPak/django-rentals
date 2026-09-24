"""Business rules for rental bookings, independent of any API layer."""

from django.core.exceptions import ValidationError

from django_rentals.models import RentalBooking

DATES_OUT_OF_ORDER = "end_date must be on or after start_date."


def validate_rental_dates(start_date, end_date):
    """Raise a ValidationError when the range ends before it starts."""
    if end_date < start_date:
        raise ValidationError(DATES_OUT_OF_ORDER)


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

    Prices the booking at the availability's per-day price times the number
    of days. It doesn't check or reduce `units_available` yet, so a listing
    can be double-booked.
    """
    validate_rental_dates(start_date, end_date)
    days = (end_date - start_date).days + 1
    return RentalBooking.objects.create(
        availability=availability,
        full_name=full_name,
        email=email,
        phone_number=phone_number,
        start_date=start_date,
        end_date=end_date,
        message=message,
        created_by=created_by,
        total_price=availability.effective_price_per_day * days,
    )
