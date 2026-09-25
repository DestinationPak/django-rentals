from django.db import models
from django.utils.timezone import localdate, now

from django_rentals.choices import RentalListingStatus


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class RentalOperatorQuerySet(ActiveQuerySet):
    def active(self):
        return super().active().filter(verified=True)


class RentalListingQuerySet(ActiveQuerySet):
    def active(self):
        return super().active().filter(operator__verified=True)

    def published(self):
        """Listings the public can see and book: published, active, operator verified."""
        return self.active().filter(status=RentalListingStatus.PUBLISHED)


class RentalAvailabilityQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(date__gte=now())

    def open(self):
        """
        Dates a guest may book, whether or not units are left.

        Leaves out past dates and listings the public can't see (the
        `RentalListing.objects.published()` rules).
        """
        return self.filter(
            date__gte=localdate(),
            listing__status=RentalListingStatus.PUBLISHED,
            listing__is_active=True,
            listing__operator__verified=True,
        )

    def bookable(self):
        """Open dates with a unit left, earliest first."""
        return self.open().filter(units_available__gt=0).order_by("date")


class RentalBookingQuerySet(models.QuerySet):
    def matching_guest(self, number, *, email=None):
        """
        The booking a guest proves they own, by `number` plus `email`.

        Never matches on `number` alone, so a guessed or leaked reference
        number can't pull up someone else's booking. `email` matches
        case-insensitively.
        """
        if not email:
            return self.none()
        return self.filter(number=number, email__iexact=email)
