from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from django_rentals.api import views

app_name = "rentals-api"

router = DefaultRouter()
router.register(r"listings", views.RentalListingViewSet, basename="listing")

app_urlpatterns = [
    path(
        "operators/",
        views.RentalOperatorListAPIView.as_view(),
        name="operators",
    ),
    path(
        "bookings/create/",
        views.RentalBookingCreateView.as_view(),
        name="bookings-create",
    ),
    path(
        "bookings/lookup/",
        views.RentalBookingLookupView.as_view(),
        name="bookings-lookup",
    ),
    *router.urls,
]

schema_urls = [
    # urlconf pins the generator to this module alone, matching django_trips'
    # own pattern - unset, drf-spectacular would walk the *host* project's
    # ROOT_URLCONF instead of just this lib's endpoints.
    path(
        "schema/",
        SpectacularAPIView.as_view(
            urlconf="django_rentals.api.urls",
            custom_settings={
                "TITLE": "Django Rentals API",
                "DESCRIPTION": "Django Rentals management restful API",
                "VERSION": "1.0.0",
            },
        ),
        name="schema",
    ),
    path(
        "schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="rentals-api:schema"),
        name="swagger-ui",
    ),
    path(
        "schema/redoc/",
        SpectacularRedocView.as_view(url_name="rentals-api:schema"),
        name="redoc",
    ),
]

urlpatterns = [*app_urlpatterns, *schema_urls]
