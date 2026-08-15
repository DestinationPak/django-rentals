# Django Rentals API

A Django REST API for vehicle/gear rental operators, listings, availability, and bookings —
the sibling package to [django-trips](https://pypi.org/project/django-trips/), part of the
[DestinationPak](https://destinationpak.com) platform.

## Installation

```bash
pip install django-rentals
```

## Usage

Add the app to your installed apps:

```python
INSTALLED_APPS = [
    ...
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

## Development

All development happens inside Docker (`make dev.up`, `make update_db`, `make test`,
`make random_rentals`) — see the Makefile (`make help` lists every target).
