# Django Rentals

[![PyPI version](https://img.shields.io/pypi/v/django-rentals.svg)](https://pypi.org/project/django-rentals/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-rentals.svg)](https://pypi.org/project/django-rentals/)
[![License](https://img.shields.io/pypi/l/django-rentals.svg)](https://github.com/DestinationPak/django-rentals/blob/main/LICENSE)
[![Unit Tests](https://github.com/DestinationPak/django-rentals/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/DestinationPak/django-rentals/actions/workflows/unit-tests.yml)

A Django app for vehicle/gear rental operators, listings, availability, and bookings: models,
querysets, business rules and admin. It's the sibling package to
[django-trips](https://pypi.org/project/django-trips/), part of the
[DestinationPak](https://destinationpak.com) platform. It ships no API or URLs: build your own
endpoints on the services and querysets described under "Business rules" below. (The DRF API it
shipped in 0.x was removed in 1.0.0; see the changelog.)

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

## Business rules

The booking and availability rules live in `django_rentals.services` and the model querysets,
so any caller (your own API, a management command, the admin) gets the same behaviour:

```python
from django_rentals.models import RentalAvailability, RentalBooking, RentalListing
from django_rentals.services import cancel_rental_booking, create_rental_booking

listings = RentalListing.objects.published()               # published, active, verified operator
open_dates = RentalAvailability.objects.bookable()          # in stock, on a published listing
booking = create_rental_booking(
    availability, full_name="Ayesha Khan", email="ayesha@example.com",
    phone_number="+923001234567", start_date=start, end_date=end,
)                                                            # per-day price x days, inclusive
cancel_rental_booking(booking)                               # gives the units back
found = RentalBooking.objects.matching_guest(number, email="ayesha@example.com")
```

`create_rental_booking` takes the listing's availability row for `start_date`. Every day in the
range needs a row with a unit left, and each of those rows gives up one unit, under a row lock
so two bookings can't both take the last unit on a day. It raises Django's `ValidationError`
when the range ends before it starts, and (keyed by `availability`) when the row isn't the
start date's or a day has no unit left. `cancel_rental_booking` gives one unit back on each day,
and raises `ValidationError` for a booking that is already cancelled or can't be cancelled.
`matching_guest` never matches on the booking number alone.

## Custom Location model

`django_rentals.Location` (a plain `name`/`slug`/`lat`/`lng` model - no region/parent
hierarchy, unlike `django_trips.Location`) is swappable, the same way Django's own
`AUTH_USER_MODEL` is. `RentalListing.location` is the only location field on `RentalListing`
now - the original free-text `RentalListing.city` field has been dropped. If you're upgrading
from a version that still had it, a prior migration best-effort backfilled `location` from each
existing `city` string before `city` itself was removed.

Two settings, both optional and both defaulting to this package's own bundled model:

- **`DJANGO_RENTALS_LOCATION_MODEL`** - an `"app_label.ModelName"` string naming which model
  actually satisfies the FK, e.g. `DJANGO_RENTALS_LOCATION_MODEL = "myapp.City"`. Your model
  doesn't need to share `Location`'s field names.
- **`DJANGO_RENTALS_LOCATION_ADAPTER`** - a dotted path to a `django_rentals.location_adapter
  .LocationAdapter` subclass telling this app how to read your model's fields as if they were
  `Location`'s (`get_name`, `get_slug`, `get_lat`, `get_lng`). Read location fields through
  `get_location_adapter()` rather than by field name, so your adapter is the only place that needs
  to know your model's real shape.

Building a brand-new Location model rather than reusing one you already have? Inherit
`django_rentals.models.AbstractLocation` instead of writing an adapter - it's a plain abstract
Django model (the same shape `AbstractUser` is - real fields and concrete methods, not an
interface class) already carrying `name`/`slug`/`lat`/`lng` and their read methods, so you get
a working swap with no `DJANGO_RENTALS_LOCATION_ADAPTER` at all:

```python
# myapp/models.py
from django_rentals.models import AbstractLocation

class MyLocation(AbstractLocation):
    city_code = models.CharField(max_length=10)
```

```python
# settings.py
DJANGO_RENTALS_LOCATION_MODEL = "myapp.MyLocation"
```

Reusing an existing model instead - one you can't restructure, or one shared with other
libraries - stick with the adapter approach above; that's what it's for.

**Set both before your project's first `migrate`.** Like `AUTH_USER_MODEL`, this is a
swappable-model setting - Django resolves it once when the app loads, and a swap made after
`Location`'s own table has already been created (and other tables have already foreign-keyed
into it) doesn't retroactively move that data; it needs a real data migration instead of a
config change.

For a worked example of a real swap: the DestinationPakistan platform (this package's own
primary consumer, a private project) points this setting directly at its own `public.Location`
model, with no adapter override at all - `public.Location` already has `name`/`slug`/`lat`, plus
an `lng` property alias (its own field is `lon`, matching django-trips' naming), so the default
`LocationAdapter` reads it correctly with no subclass. See `docs/location-model-swap-design.md`
in that project for the full writeup.

## Development

All development happens inside Docker (`make dev.up`, `make update_db`, `make test`,
`make random_rentals`) — see the Makefile (`make help` lists every target).

## Documentation

This README is also published as browsable docs (`docs/`, built with Sphinx). Build it
locally with:
```bash
pip install -e ".[docs]"
sphinx-build -b html docs docs/_build
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development/release workflow, and the
[Code of Conduct](CODE_OF_CONDUCT.md). Found a security issue? See
[SECURITY.md](SECURITY.md) rather than opening a public issue.
