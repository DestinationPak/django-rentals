from rest_framework import generics, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from django_rentals.api.serializers import (
    RentalBookingCreateSerializer,
    RentalBookingSerializer,
    RentalListingSerializer,
    RentalOperatorSerializer,
)
from django_rentals.choices import RentalBookingStatus, RentalListingStatus
from django_rentals.models import RentalBooking, RentalListing, RentalOperator


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
        # `operator__verified=True` here mirrors django_hotels.Hotel.objects
        # .active()'s owner__verified check - an unverified operator's
        # listings must not be publicly bookable just because the listing
        # itself is published/active.
        return (
            RentalListing.objects.filter(
                status=RentalListingStatus.PUBLISHED,
                is_active=True,
                operator__verified=True,
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
    """
    Anonymous "look up my booking" endpoint.

    Scoped to a booking `number` AND `email` together - never `number`
    alone, so a guessed or leaked reference number can't be used to
    pull up someone else's booking (mirrors django_hotels'
    HotelBookingLookupView fix for the same booking IDOR, destipak's
    docs/multi-tenancy-design.md Section 4). Both are explicitly
    required rather than left to fall out of `email=None` never
    matching a non-nullable column - that's an accident of schema, not
    an enforced rule.
    """

    serializer_class = RentalBookingSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        number = self.request.query_params.get("number")
        email = self.request.query_params.get("email")
        if not number or not email:
            raise ValidationError(
                {"detail": "`number` and `email` query parameters are required."}
            )
        return generics.get_object_or_404(
            RentalBooking.objects.all(), number=number, email__iexact=email
        )


class RentalBookingRetrieveUpdateViewSet(GenericViewSet, generics.RetrieveUpdateAPIView):
    """
    Authenticated "my booking" retrieve/update/cancel.

    Scoped to `created_by=request.user`, never `RentalBooking.objects.all()`
    - mirrors django_hotels' HotelBookingRetrieveUpdateViewSet fix for the
    same booking IDOR (destipak's docs/multi-tenancy-design.md Section 4),
    so one user can't retrieve, update, or cancel another user's booking
    by guessing its reference number. Session-only auth, same as
    HotelBookingRetrieveUpdateViewSet - this package doesn't depend on
    djangorestframework-simplejwt; a consuming project mounting this
    endpoint behind its own JWT-authenticated frontend adds that at its
    own layer instead (see destipak's `djangoapps/hotel_owners`' operator
    viewsets for that pattern).
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [SessionAuthentication]
    serializer_class = RentalBookingCreateSerializer
    lookup_field = "number"
    http_method_names = ["get", "put", "post"]

    def get_queryset(self):
        return RentalBooking.objects.filter(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def cancel(self, request, *args, **kwargs):  # pylint:disable=unused-argument
        booking = self.get_object()
        if RentalBookingStatus.is_cancelled(booking.status):
            return Response(
                {"detail": "Booking is already cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not booking.can_be_cancelled():
            return Response(
                {"detail": "Booking cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        booking.cancel()
        # RentalBookingCreateSerializer (this viewset's serializer_class,
        # shared with retrieve/update) has no `status` field - the fuller
        # read serializer is used here so the response actually shows the
        # cancellation that just happened.
        return Response(RentalBookingSerializer(booking).data)
