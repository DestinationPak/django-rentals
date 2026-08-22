# Django Rentals API

[![PyPI version](https://img.shields.io/pypi/v/django-rentals.svg)](https://pypi.org/project/django-rentals/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-rentals.svg)](https://pypi.org/project/django-rentals/)
[![License](https://img.shields.io/pypi/l/django-rentals.svg)](https://github.com/DestinationPak/django-rentals/blob/master/LICENSE)
[![Unit Tests](https://github.com/DestinationPak/django-rentals/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/DestinationPak/django-rentals/actions/workflows/unit-tests.yml)

A Django REST API for vehicle/gear rental operators, listings, availability, and bookings —
the sibling package to [django-trips](https://pypi.org/project/django-trips/), part of the
[DestinationPak](https://destinationpak.com) platform.

## Installation

```bash
pip install django-rentals
```

## Usage

Add the app (and `django_filters`, used by the catalog/availability filtering below) to
your installed apps:

```python
INSTALLED_APPS = [
    ...
    'django_filters',
    'django_rentals',
]
```

## Migrate

```bash
python manage.py migrate
```

Mount its urls under a namespace of your choosing:

```python
urlpatterns = [
    ...
    path('rentals/', include('django_rentals.urls')),
]
```

This mounts the whole app under your own chosen prefix (`rentals/` above) with the lib's
own `v1/` version underneath it, e.g. `rentals/v1/listings/`,
`rentals/v1/schema/redoc/`. The app versions itself independently of your project's own
API version.

## Domain model

`RentalOperator` (the tenant/owner entity, mirrors `django_trips.Host`) → `RentalListing`
(one bookable vehicle or gear kit, mirrors `Trip`) → `RentalAvailability` (a bookable date,
mirrors `TripSchedule`) → `RentalBooking` (mirrors `TripBooking`, but books a
`start_date`/`end_date` range rather than a single departure date).

There is deliberately no separate tier/package model the way `django_trips` has
`TripPackage` — a distinct `RentalListing` per vehicle/kit already serves that purpose.

Like `django_trips`, this package is tenancy-oblivious: it has no concept of which user is
allowed to manage a given `RentalOperator`. That authorization layer belongs to whichever
project installs this app (see destipak's `docs/multi-tenancy-design.md` for the pattern
this is meant to plug into).

## Public API

Read-only and unauthenticated (`AllowAny`) unless noted:

- `listings/` - the published catalog. Filterable via query params: `?category=`, `?city=`,
  `?operator=<id>`.
- `listings/<slug>/` - one listing's detail, including its images and availabilities.
- `operators/` - active, verified `RentalOperator`s.
- `availabilities/` - date-range availability search across active listings. Filterable via
  `?listing=<slug>`, `?date_from=`, `?date_to=` (any combination; omitting all three returns
  every upcoming bookable date).
- `bookings/create/` - guest booking (no auth required).
- `bookings/lookup/?number=&email=` - guest "find my booking".
- `bookings/<number>/` - authenticated traveller's own booking (retrieve/update/cancel).
- `schema/`, `schema/swagger-ui/`, `schema/redoc/` - this app's own OpenAPI schema, scoped
  to just these endpoints regardless of what else your project mounts.

## Custom Location model

`django_rentals.Location` (a plain `name`/`slug`/`lat`/`lng` model - no region/parent
hierarchy, unlike `django_trips.Location`) is swappable, the same way Django's own
`AUTH_USER_MODEL` is. `RentalListing.location` is a nullable FK to it, added alongside the
pre-existing `RentalListing.city` `CharField` - `city` is **not removed**, since a data
migration (`migrations/0003_backfill_location_from_city.py`) only best-effort backfills
`location` from `city` by matching string; `city` stays until every consumer (destipak
included) has finished backfilling against its own chosen Location model.

Two settings, both optional and both defaulting to this package's own bundled model:

- **`DJANGO_RENTALS_LOCATION_MODEL`** - an `"app_label.ModelName"` string naming which model
  actually satisfies the FK, e.g. `DJANGO_RENTALS_LOCATION_MODEL = "myapp.City"`. Your model
  doesn't need to share `Location`'s field names.
- **`DJANGO_RENTALS_LOCATION_ADAPTER`** - a dotted path to a `django_rentals.location_adapter
  .LocationAdapter` subclass telling this app how to read your model's fields as if they were
  `Location`'s (`get_name`, `get_slug`, `get_lat`, `get_lng`). Nothing in this package's own
  serializers reads `location`'s fields yet (`city` is still what's exposed in API output) -
  the adapter exists as the swap-point infrastructure, ready for whichever consumer project
  (or a later ticket here) actually surfaces `location` in output.

**Set both before your project's first `migrate`.** Like `AUTH_USER_MODEL`, this is a
swappable-model setting - Django resolves it once when the app loads, and a swap made after
`Location`'s own table has already been created (and other tables have already foreign-keyed
into it) doesn't retroactively move that data; it needs a real data migration instead of a
config change.

For a worked example of a real swap: the DestinationPakistan platform (this package's own
primary consumer, a private project) points this setting at its own `public.City` model via a
`HotelsRentalsCityLocationAdapter` in its `djangoapps/public/adapters.py` - the same shape
sketched above, just concretely filled in.

## Development

All development happens inside Docker (`make dev.up`, `make update_db`, `make test`,
`make random_rentals`) — see the Makefile (`make help` lists every target).
