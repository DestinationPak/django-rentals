"""
django_rentals models.

This package is deliberately tenancy-oblivious, mirroring django_trips: it has
no concept of which user may manage a RentalOperator. That's a consuming
project's job (see destipak's `djangoapps/hosts/` for the equivalent seam
built for django_trips's Host) - not something this package builds a hook for.
"""

import random

import swapper
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from django_rentals.choices import RentalBookingStatus, RentalCategory, RentalListingStatus
from django_rentals.managers import (
    RentalAvailabilityQuerySet,
    RentalListingQuerySet,
    RentalOperatorQuerySet,
)


class AbstractLocation(models.Model):
    """
    Base fields and behavior for a Location model.

    Inherit this to build a custom Location model instead of writing a
    LocationAdapter subclass - you get these fields and methods for
    free and only override what needs to change. See the README's
    "Custom Location model" section for when to reach for this versus
    the adapter.

    Deliberately minimal - no region/parent hierarchy, since Rentals
    has no such concept.
    """

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True, null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return f"<Location: {self.name} slug: {self.slug}>"


class Location(AbstractLocation):
    """This package's own default, concrete Location model."""

    class Meta(AbstractLocation.Meta):
        swappable = swapper.swappable_setting("django_rentals", "Location")


def get_location_model():
    """Location, or whichever model DJANGO_RENTALS_LOCATION_MODEL swaps it
    for."""
    return swapper.load_model("django_rentals", "Location")


class RentalOperator(models.Model):
    """
    A rental business (vehicle/gear) - the tenant/owner entity, mirroring
    django_trips.Host. Plain domain model: no login/auth fields.
    """

    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=70, unique=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    mobile = models.CharField(max_length=15, null=True, blank=True)
    cancellation_policy = models.JSONField(default=list, blank=True, null=True)
    refund_policy = models.JSONField(default=list, blank=True, null=True)
    verified = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        help_text="Deactivating an operator also deactivates all of their "
        "listings, hiding them from the public API.",
    )

    objects = RentalOperatorQuerySet.as_manager()

    class Meta:
        ordering = ["name", "verified"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return f"<RentalOperator: {self.name} slug: {self.slug}>"


class RentalListing(models.Model):
    """
    One bookable vehicle or gear kit, mirroring django_trips.Trip. There is
    deliberately no separate tier/package model (unlike Trip's TripPackage) -
    a distinct RentalListing per vehicle/kit already serves that purpose.
    """

    name = models.CharField("Title", max_length=255)
    slug = models.SlugField(max_length=255, unique=True, null=True, blank=True)
    operator = models.ForeignKey(
        RentalOperator,
        related_name="listings",
        on_delete=models.CASCADE,
        help_text="Operator responsible for this listing",
    )
    category = models.CharField(
        max_length=20, choices=RentalCategory.choices, default=RentalCategory.VEHICLE
    )
    city = models.CharField(max_length=100, null=True, blank=True)
    location = models.ForeignKey(
        swapper.get_model_name("django_rentals", "Location"),
        null=True,
        blank=True,
        related_name="listings",
        on_delete=models.SET_NULL,
        help_text="Structured location, backfilled from `city` (P9.4) - "
        "`city` stays in place until after destipak's own swap+reconcile "
        "(P9.5/P9.6) lands.",
    )
    description = models.TextField(blank=True, null=True)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=RentalListingStatus.choices,
        default=RentalListingStatus.PUBLISHED,
        help_text="Editorial state (draft/published) - independent of is_active",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="rental_listings", on_delete=models.CASCADE
    )

    objects = RentalListingQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return f"<RentalListing: {self.name} operator: {self.operator_id}>"


class RentalAvailability(models.Model):
    """
    A specific bookable date for a listing, mirroring django_trips.TripSchedule.
    """

    listing = models.ForeignKey(
        RentalListing, related_name="availabilities", on_delete=models.CASCADE
    )
    date = models.DateField()
    price_per_day = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        null=True,
        blank=True,
        help_text="Overrides the listing's own price_per_day for this date when set.",
    )
    units_available = models.PositiveIntegerField(default=1)

    objects = RentalAvailabilityQuerySet.as_manager()

    class Meta:
        ordering = ["date"]
        verbose_name_plural = "Rental availabilities"

    @property
    def effective_price_per_day(self):
        return self.price_per_day or self.listing.price_per_day

    def __str__(self):
        return f"{self.listing} - {self.date}"


class RentalImage(models.Model):
    listing = models.ForeignKey(
        RentalListing, related_name="images", on_delete=models.CASCADE
    )
    image = models.URLField()
    caption = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.listing} image #{self.order}"


class RentalBooking(models.Model):
    """
    A customer's booking against a RentalAvailability, mirroring
    django_trips.TripBooking - guest or logged-in, staff-mediated status flow.
    Books a date range (start_date/end_date) rather than a single date, since
    a rental is held for a span of days, not one departure date.
    """

    number = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        help_text="Auto-generated booking reference number",
    )
    otp = models.CharField(
        max_length=4,
        editable=False,
        help_text="Auto-generated 4-digit code, shown once at booking creation. "
        "Paired with `number` as an alternative to `number` + `email` for the "
        "guest booking lookup endpoint.",
    )
    availability = models.ForeignKey(
        RentalAvailability, related_name="bookings", on_delete=models.CASCADE
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=30)

    start_date = models.DateField()
    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=RentalBookingStatus.choices,
        default=RentalBookingStatus.PENDING,
    )
    message = models.TextField(null=True, blank=True)
    total_price = models.DecimalField(default=0, max_digits=10, decimal_places=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="rental_bookings",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Null for guest bookings.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.number} - {self.full_name}"

    def __repr__(self):
        return f"<RentalBooking - {self.number}, {self.status}>"

    def save(self, **kwargs):
        if not self.number:
            self.number = self.generate_booking_number()
        if not self.otp:
            self.otp = self.generate_otp()
        super().save(**kwargs)

    def can_be_cancelled(self):
        return RentalBookingStatus.can_be_cancelled(self.status)

    def cancel(self):
        self.status = RentalBookingStatus.CANCELLED
        self.save(update_fields=["status", "updated_at"])

    @classmethod
    def generate_booking_number(cls):
        """
        DPR00000107
        DPR00000284
        Mirrors django_trips.TripBooking.generate_booking_number's mechanism
        with a distinct prefix so Rentals references are visually
        distinguishable from Trips'.
        """
        prefix = "DPR"
        count = cls.objects.count() + 1
        padded_number = f"{count:06d}"
        suffix = f"{random.randint(0, 99):02d}"
        return f"{prefix}{padded_number}{suffix}"

    @classmethod
    def generate_otp(cls):
        """A random 4-digit code. Not checked for uniqueness - it's only
        ever looked up together with `number`, which is unique."""
        return f"{random.randint(0, 9999):04d}"
