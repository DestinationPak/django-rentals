"""Urls for the rentals app"""

from django.urls import include, path

urlpatterns = [
    path(
        # The lib owns its own version, independent of whatever prefix/version
        # scheme the consuming project uses for its own endpoints - see README "Usage".
        "v1/",
        include(("django_rentals.api.urls", "rentals-api"), namespace="rentals-api"),
    ),
]
