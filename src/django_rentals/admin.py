import swapper
from django import forms
from django.contrib import admin

from django_rentals.choices import RentalBookingStatus
from django_rentals.models import (
    Location,
    RentalAvailability,
    RentalBooking,
    RentalImage,
    RentalListing,
    RentalOperator,
)
from django_rentals.services import cancel_rental_booking, delete_rental_booking


class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "lat", "lng"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


# Registering LocationAdmin against django_rentals.Location only makes
# sense while it's actually the active model - once
# DJANGO_RENTALS_LOCATION_MODEL is swapped, this table/model isn't
# migrated at all.
if not swapper.is_swapped("django_rentals", "Location"):
    admin.site.register(Location, LocationAdmin)


@admin.register(RentalOperator)
class RentalOperatorAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "verified", "is_active"]
    search_fields = ["name", "email"]
    list_filter = ["verified", "is_active"]


@admin.register(RentalListing)
class RentalListingAdmin(admin.ModelAdmin):
    # No autocomplete_fields for location - it would require LocationAdmin
    # to always be registered, which isn't true once Location is swapped.
    list_display = ["name", "operator", "category", "location", "status", "is_active"]
    list_filter = ["category", "status", "is_active"]
    search_fields = ["name", "location__name"]


@admin.register(RentalAvailability)
class RentalAvailabilityAdmin(admin.ModelAdmin):
    list_display = ["listing", "date", "effective_price_per_day", "units_available"]
    list_filter = ["date"]


@admin.register(RentalImage)
class RentalImageAdmin(admin.ModelAdmin):
    list_display = ["listing", "order", "caption"]


REOPEN_NOT_ALLOWED = (
    "A cancelled booking can't be reopened, since its units may be taken by now. "
    "Create a new booking instead."
)


class RentalBookingAdminForm(forms.ModelForm):
    class Meta:
        model = RentalBooking
        fields = "__all__"

    def clean_status(self):
        status = self.cleaned_data["status"]
        if (
            self.instance.pk
            and RentalBookingStatus.is_cancelled(self.instance.status)
            and not RentalBookingStatus.is_cancelled(status)
        ):
            raise forms.ValidationError(REOPEN_NOT_ALLOWED)
        return status


@admin.register(RentalBooking)
class RentalBookingAdmin(admin.ModelAdmin):
    """
    Bookings, kept in step with their availability.

    Cancelling or deleting a booking here gives its units back, a cancelled
    booking can't be reopened, and the fields that decide what a booking
    holds are read-only once it exists.
    """

    form = RentalBookingAdminForm
    capacity_fields = ("availability", "start_date", "end_date")
    list_display = ["number", "full_name", "email", "start_date", "end_date", "status"]
    list_filter = ["status"]
    search_fields = ["number", "email", "full_name"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        return (*readonly_fields, *self.capacity_fields) if obj else readonly_fields

    def save_model(self, request, obj, form, change):
        cancelling = (
            change
            and "status" in form.changed_data
            and RentalBookingStatus.is_cancelled(obj.status)
        )
        if cancelling:
            obj.status = form.initial["status"]
        super().save_model(request, obj, form, change)
        if cancelling:
            cancel_rental_booking(obj, check_cancellable=False)

    def delete_model(self, request, obj):
        delete_rental_booking(obj)

    def delete_queryset(self, request, queryset):
        for booking in queryset:
            delete_rental_booking(booking)
