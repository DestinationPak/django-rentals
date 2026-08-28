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
skips drf-spectacular schema annotations beyond the bare minimum. That's a fast-follow, not an
omission to "fix" without checking with the maintainer first.

## Common commands

All development happens inside Docker; there is no supported bare-metal workflow.

```bash
make build           # docker compose build (destroys existing containers first)
make dev.up           # start web + mysql containers
make shell            # attach a shell inside the web container
make update_db         # run migrations
make random_rentals     # seed random rental operators/listings (generate_rentals --batch_size=100)
make test             # docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=settings.test web pytest
make stop / make destroy  # stop / tear down containers (destroy removes volumes too)
make logs             # tail web container logs
```

`make test` explicitly overrides `DJANGO_SETTINGS_MODULE` and skips the `database` dependency -
`settings/test.py` swaps in an in-memory SQLite `DATABASES`, but `docker-compose.yml`'s `web`
service sets `DJANGO_SETTINGS_MODULE=settings.common` as a container-wide environment variable,
which pytest-django only ever uses as a fallback (`os.environ.setdefault`, never overriding an
already-set var) - so without the explicit `-e` override, `pytest.ini`'s own
`DJANGO_SETTINGS_MODULE = settings.test` is silently ignored and tests run against real MySQL
instead, which also makes `--no-deps` (skip starting the `database` container) unsafe to combine
with the plain `docker compose run --rm web pytest` form.

Running a single test (inside the container, e.g. via `make shell`):

```bash
pytest django_rentals/tests/test_models.py
```

Test settings use `settings.test` (`DJANGO_SETTINGS_MODULE=settings.test` per `pytest.ini`), which imports
`settings.common` but swaps `DATABASES` to an in-memory SQLite backend - combined with `--no-migrations`,
tests build schema directly from models against SQLite, not the MySQL real deployments run against.

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
- `Location` (plain `name`/`slug`/`lat`/`lng`, no hierarchy — unlike `django_trips.Location`'s
  `type`/`parent`) is swappable via `swapper` (see README's "Custom Location model"), the same
  mechanism `django_trips.Location`/`django_hotels.Location` use. `RentalListing.location`
  (nullable FK) is now the only location field on `RentalListing` - the original free-text
  `RentalListing.city` `CharField` (`migrations/0003_backfill_location_from_city.py` best-effort
  backfilled `location` from it by string match) has been dropped
  (`migrations/0004_remove_rentallisting_city.py`), once every consumer (destipak included) had
  finished backfilling against its own chosen Location model. `django_rentals/location_adapter.py`
  (`LocationAdapter`/`get_location_adapter()`, `DJANGO_RENTALS_LOCATION_ADAPTER`) is the read path
  for location fields, mirroring `django_trips/location_adapter.py` one vertical over -
  `RentalListingSerializer` now exposes `location` as a nested object through the adapter (via
  this package's own `LocationSerializer`), and `?location=<id>` filters on it directly.
  `AbstractLocation` (`models.py`) is a plain abstract Django model -
  the same shape `AbstractUser` is, real fields and concrete methods, not an interface class - an
  installer building a brand-new custom Location model can inherit directly instead of writing a
  `LocationAdapter` subclass; see README's "Custom Location model" for when to reach for which.

### Tenancy-oblivious, on purpose

This package has **zero concept of who's allowed to manage a `RentalOperator`** — no membership model,
no permission classes, no auth. That's a deliberate mirror of `django_trips`' own architecture (see
destipak's `docs/multi-tenancy-design.md` §2): the domain library stays tenancy-oblivious, and whichever
project installs this app owns the login/permission/scoping layer on top (destipak's
`djangoapps/rental_operators/`, built against `RentalOperator` instead of `Host`/`HotelOwner`). Do not
add auth/permission/ownership-membership code to this package.

### API layer

`django_rentals/api/urls.py` wires a `DefaultRouter` (`RentalListingViewSet` read-only;
`RentalBookingRetrieveUpdateViewSet` for the authenticated "my booking" retrieve/update/cancel, scoped
to `created_by=request.user`) plus explicit `path()` entries for operators list, booking create
(`AllowAny`), and booking lookup (by `number` + `email` together, case-insensitive, never `number`
alone — mirrors `django_hotels.HotelBookingLookupView`'s fixed shape, itself mirroring
`TripBookingLookupView`). `RentalListingViewSet` is deliberately read-only (`ReadOnlyModelViewSet`) —
create/update/destroy belong to the consuming project's operator-facing surface, not this package, same
split `django_trips.TripViewSet` uses post-hardening.

### Settings

`settings/common.py` is the real settings module for local dev (Docker sets
`DJANGO_SETTINGS_MODULE=settings.common`); `settings/test.py` re-exports it for pytest but swaps
`DATABASES` to an in-memory SQLite backend (see "Common commands" above for how `make test` forces
this to actually take effect). `django-rentals/wsgi.py`/`asgi.py`/`urls.py` are the minimal dev-only
project shell and aren't part of the published package.

## Testing conventions

Write tests as `django.test.TestCase` subclasses (`unittest`-style classes), not bare
`@pytest.mark.django_db`-decorated functions — group related cases under one class per
model/view/concern, matching `django_hotels`' and `djangoapps/hotel_owners`' convention one vertical
over. Build fixtures via `django_rentals/tests/factories.py` (`RentalOperatorFactory`,
`RentalListingFactory`, `RentalAvailabilityFactory`, `RentalBookingFactory`, `UserFactory`) rather than
calling `Model.objects.create(...)` directly in a test - mirrors `django_hotels/tests/factories.py`'s
own convention. Consuming projects (destipak's `djangoapps/rental_operators/`) should do the same when
their own tests need a fixture, since this module is importable wherever the package is installed
(it's shipped as part of `django_rentals`, not test-only-excluded). A raw `.objects.create()` is still
fine for a test whose whole point is model/manager mechanics (e.g. `test_models.py`'s slug/booking-number
generation and `.active()` filter tests) rather than needing an incidental fixture.
