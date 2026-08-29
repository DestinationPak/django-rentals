import swapper
from django.contrib import admin

from django_rentals.models import (
    Location,
    RentalAvailability,
    RentalBooking,
    RentalImage,
    RentalListing,
    RentalOperator,
)


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


@admin.register(RentalBooking)
class RentalBookingAdmin(admin.ModelAdmin):
    list_display = ["number", "full_name", "email", "start_date", "end_date", "status"]
    list_filter = ["status"]
    search_fields = ["number", "email", "full_name"]
