from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from django_rentals import services
from django_rentals.location_adapter import get_location_adapter
from django_rentals.models import (
    RentalAvailability,
    RentalBooking,
    RentalImage,
    RentalListing,
    RentalOperator,
)


class LocationSerializer(serializers.Serializer):  # pylint:disable=abstract-method
    """
    A plain Serializer, not a ModelSerializer - every field is read
    through get_location_adapter() rather than by name off the model
    directly, so this keeps working whether django_rentals.Location or a
    swapped-in model (DJANGO_RENTALS_LOCATION_MODEL) backs the FK.
    """

    name = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    def get_name(self, location):
        return get_location_adapter().get_name(location)

    def get_slug(self, location):
        return get_location_adapter().get_slug(location)

    def get_lat(self, location):
        return get_location_adapter().get_lat(location)

    def get_lng(self, location):
        return get_location_adapter().get_lng(location)


class RentalOperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalOperator
        fields = ["id", "name", "slug", "description", "verified"]


class RentalImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalImage
        fields = ["id", "image", "caption", "order"]


class RentalAvailabilitySerializer(serializers.ModelSerializer):
    effective_price_per_day = serializers.DecimalField(
        max_digits=10, decimal_places=0, read_only=True
    )

    class Meta:
        model = RentalAvailability
        fields = ["id", "date", "effective_price_per_day", "units_available"]


class RentalAvailabilityListingSerializer(serializers.ModelSerializer):
    """Minimal listing context for an availability-search row."""

    class Meta:
        model = RentalListing
        fields = ("id", "name", "slug")


class RentalAvailabilitySearchSerializer(serializers.ModelSerializer):
    """
    Availability-search row shape, spanning multiple listings.

    RentalAvailabilitySerializer (embedded under RentalListingSerializer,
    where the parent already gives listing context) intentionally stays
    lighter.
    """

    effective_price_per_day = serializers.DecimalField(
        max_digits=10, decimal_places=0, read_only=True
    )
    listing = RentalAvailabilityListingSerializer(read_only=True)

    class Meta:
        model = RentalAvailability
        fields = ["id", "listing", "date", "effective_price_per_day", "units_available"]


class RentalListingSerializer(serializers.ModelSerializer):
    """Public read-only listing serializer - list and detail both use this
    for now (a "basic" scaffold doesn't yet need a separate lighter list
    shape the way TripListSerializer/TripDetailSerializer split in django_trips)."""

    operator = RentalOperatorSerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    images = RentalImageSerializer(many=True, read_only=True)
    availabilities = RentalAvailabilitySerializer(many=True, read_only=True)

    class Meta:
        model = RentalListing
        fields = [
            "id",
            "name",
            "slug",
            "operator",
            "category",
            "location",
            "description",
            "price_per_day",
            "status",
            "images",
            "availabilities",
        ]


class RentalBookingCreateSerializer(serializers.ModelSerializer):
    """Guest booking create - mirrors django_trips.TripBookingCreateView's
    intent: AllowAny, computes total_price server-side from the date range."""

    class Meta:
        model = RentalBooking
        fields = [
            "availability",
            "full_name",
            "email",
            "phone_number",
            "start_date",
            "end_date",
            "message",
        ]

    def validate(self, attrs):
        try:
            services.validate_rental_dates(attrs["start_date"], attrs["end_date"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0]) from exc
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        created_by = request.user if request and request.user.is_authenticated else None
        return services.create_rental_booking(created_by=created_by, **validated_data)


class RentalBookingSerializer(serializers.ModelSerializer):
    """Read shape returned after create, and for the guest lookup endpoint."""

    class Meta:
        model = RentalBooking
        fields = [
            "number",
            "otp",
            "availability",
            "full_name",
            "email",
            "phone_number",
            "start_date",
            "end_date",
            "status",
            "total_price",
            "created_at",
        ]
        read_only_fields = fields
