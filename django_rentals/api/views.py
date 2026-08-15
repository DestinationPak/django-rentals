from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from django_rentals.choices import RentalListingStatus
from django_rentals.models import RentalBooking, RentalListing, RentalOperator
from django_rentals.api.serializers import (
    RentalBookingCreateSerializer,
    RentalBookingSerializer,
    RentalListingSerializer,
    RentalOperatorSerializer,
)


class RentalOperatorListAPIView(generics.ListAPIView):
    """Public, read-only list of active/verified rental operators."""

    serializer_class = RentalOperatorSerializer
    permission_classes = [AllowAny]
    queryset = RentalOperator.objects.active()


class RentalListingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public catalog surface - list/retrieve only. Create/update/destroy are
    deliberately absent here, same split django_trips.TripViewSet uses:
    write access is an operator-facing, tenancy-aware concern that belongs
    in the consuming project, not this package.
    """

    serializer_class = RentalListingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            RentalListing.objects.filter(
                status=RentalListingStatus.PUBLISHED, is_active=True
            )
            .select_related("operator")
            .prefetch_related("images", "availabilities")
        )


class RentalBookingCreateView(generics.CreateAPIView):
    """Guest booking create - AllowAny, mirrors TripBookingCreateView's intent."""

    serializer_class = RentalBookingCreateSerializer
    permission_classes = [AllowAny]
    queryset = RentalBooking.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(RentalBookingSerializer(booking).data, status=201)


class RentalBookingLookupView(generics.RetrieveAPIView):
    """Guest booking lookup by reference number + email - no login needed,
    mirrors TripBookingLookupView's scoping (number AND email must match)."""

    serializer_class = RentalBookingSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        number = self.request.query_params.get("number")
        email = self.request.query_params.get("email")
        return generics.get_object_or_404(
            RentalBooking.objects.all(), number=number, email=email
        )
