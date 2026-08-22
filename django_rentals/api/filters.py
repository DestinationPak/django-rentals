"""FilterSets for django_rentals' public API."""

import django_filters

from django_rentals.models import RentalAvailability


class RentalAvailabilityFilter(django_filters.FilterSet):
    """Filters availability search by listing and date range."""

    listing = django_filters.CharFilter(field_name="listing__slug")
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = RentalAvailability
        fields = ["listing", "date_from", "date_to"]
