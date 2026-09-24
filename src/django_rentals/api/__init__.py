"""
DRF API for django-rentals, deprecated and removed in 1.0.0.

From 1.0.0 the package ships the domain only: models, querysets and
`django_rentals.services`. Build your own API on those instead.
"""

import warnings

warnings.warn(
    "django_rentals.api is deprecated and will be removed in django-rentals 1.0.0. "
    "Build your own API on django_rentals.services and the model querysets.",
    DeprecationWarning,
    stacklevel=2,
)
