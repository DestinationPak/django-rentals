# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`django-rentals` is a reusable Django app (published as a pip package, see `setup.cfg`) providing a REST
API for rental operators, listings, availability, and bookings — vehicle/gear rentals (jeep tours,
trekking equipment) for the [DestinationPak](https://destinationpak.com) platform. It's the sibling
package to `django-trips`, following the same structure, and consumers install it and mount its urls
under a namespace of their choosing (see README "Usage").

Note the two similarly-named top-level packages, same convention as django-trips: `django-rentals/`
(hyphen) is the throwaway Django *project* shell used only for local dev; `django_rentals/` (underscore)
is the actual app that gets published and contains all real logic.

This is a **basic initial scaffold**, not a full port of every django-trips feature — it deliberately
skips JWT auth, drf-spectacular schema annotations beyond the bare minimum, and a fuller test suite.
Those are fast-follows, not omissions to "fix" without checking with the maintainer first.

## Common commands

All development happens inside Docker; there is no supported bare-metal workflow.

```bash
make build           # docker compose build (destroys existing containers first)
make dev.up           # start web + mysql containers
make shell            # attach a shell inside the web container
make update_db         # run migrations
make random_rentals     # seed random rental operators/listings (generate_rentals --batch_size=100)
make test             # docker compose run --rm web pytest
make stop / make destroy  # stop / tear down containers (destroy removes volumes too)
make logs             # tail web container logs
```

Running a single test (inside the container, e.g. via `make shell`):

```bash
pytest django_rentals/tests/test_models.py
```

Test settings use `settings.test` (`DJANGO_SETTINGS_MODULE=settings.test` per `pytest.ini`), which just
imports `settings.common` with `--no-migrations` — tests build schema directly from models.

## Architecture

### Domain model shape

Everything hangs off `RentalListing` (`django_rentals/models.py`):

- `RentalListing` → `RentalOperator` (the tenant/owner entity, mirrors `django_trips.Host`) — a plain
  domain model with no login/auth fields.
- `RentalListing` → `RentalAvailability` (a specific bookable date, mirrors `TripSchedule`) →
  `RentalBooking` (mirrors `TripBooking`, but books a `start_date`/`end_date` range, not a single
  departure date — `total_price` is `effective_price_per_day * days`, computed server-side in
  `RentalBookingCreateSerializer.create()`).
- There is **no separate tier/package model** the way `django_trips` has `TripPackage` — a distinct
  `RentalListing` per vehicle/kit already serves that purpose. Don't add one without a real product
  reason; see the naming-convention discussion this repo was scaffolded from.
- `RentalBooking.generate_booking_number()` mirrors `TripBooking`'s mechanism exactly (zero-padded
  incrementing count + 2 random digits) with a distinct `DPR` prefix instead of `DPT`, so references
  are visually distinguishable from Trips bookings.

### Tenancy-oblivious, on purpose

This package has **zero concept of who's allowed to manage a `RentalOperator`** — no membership model,
no permission classes, no auth. That's a deliberate mirror of `django_trips`' own architecture (see
destipak's `docs/multi-tenancy-design.md` §2): the domain library stays tenancy-oblivious, and whichever
project installs this app owns the login/permission/scoping layer on top (an equivalent to destipak's
`djangoapps/hosts/` built against `RentalOperator` instead of `Host`). Do not add auth/permission/
ownership-membership code to this package.

### API layer

`django_rentals/api/urls.py` wires a `DefaultRouter` (`RentalListingViewSet`, read-only) plus explicit
`path()` entries for operators list, booking create, and booking lookup (by `number` + `email`, no
login — mirrors `TripBookingLookupView`). `RentalListingViewSet` is deliberately read-only
(`ReadOnlyModelViewSet`) — create/update/destroy belong to the consuming project's operator-facing
surface, not this package, same split `django_trips.TripViewSet` uses post-hardening.

### Settings

`settings/common.py` is the real settings module for local dev (Docker sets
`DJANGO_SETTINGS_MODULE=settings.common`); `settings/test.py` just re-exports it for pytest.
`django-rentals/wsgi.py`/`asgi.py`/`urls.py` are the minimal dev-only project shell and aren't part of
the published package.
