from django.contrib import admin

from django_rentals.models import (
    RentalAvailability,
    RentalBooking,
    RentalImage,
    RentalListing,
    RentalOperator,
)


@admin.register(RentalOperator)
class RentalOperatorAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "verified", "is_active"]
    search_fields = ["name", "email"]
    list_filter = ["verified", "is_active"]


@admin.register(RentalListing)
class RentalListingAdmin(admin.ModelAdmin):
    list_display = ["name", "operator", "category", "city", "status", "is_active"]
    list_filter = ["category", "status", "is_active"]
    search_fields = ["name", "city"]


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
