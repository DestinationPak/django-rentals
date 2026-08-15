from django.apps import AppConfig


class DjangoRentalsConfig(AppConfig):
    name = "django_rentals"
    verbose_name = "Django Rentals"
    # Pinned per-app so this package's models always get BigAutoField
    # regardless of the consuming project's own DEFAULT_AUTO_FIELD.
    default_auto_field = "django.db.models.BigAutoField"
