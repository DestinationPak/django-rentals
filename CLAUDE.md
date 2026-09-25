# CLAUDE.md

`django-rentals` is a reusable Django app published on PyPI: rental operators, listings, availability and bookings (vehicle and gear rentals), as models, querysets, business rules (`services.py`) and admin. It is a sibling of django-trips with the same structure. The app lives in `src/django_rentals/`; `devsite/` is a dev-only project shell.

This file holds only what every session needs. Details live in `docs/development/`; read the matching file before working in that area.

## Commands

All development runs in Docker. `make dev.up` (SQLite by default), `make shell`, `make update_db`, `make random_rentals`, `make test`. Lint with `python run_lint.py`. Inside the container, `pytest path::Class::test` runs one test.

## Git workflow

`main` is the base branch. Never commit to `main`: branch off the latest `main`, push, open a PR. Once a branch's PR merges, cut a fresh branch and cherry-pick anything unlanded. The repo lives at `DestinationPak/django-rentals`; pass `-R DestinationPak/django-rentals` to `gh` in case the local remote still points at an old URL.

## Rules that fail silently

- **No API here.** Never add a view, serializer or `urls.py`. A new rule goes in `services.py` (writes) or a queryset in `managers.py` (reads), raising `ValidationError` keyed by field.
- **No ownership or permissions here.** Who may manage a `RentalOperator` belongs to the installing project, never this package.
- **Capacity changes go through the services.** `create_rental_booking()` takes one unit per day under a row lock; `cancel_rental_booking()`/`delete_rental_booking()` give them back. The admin calls them too, so never change `units_available` or a booking's status directly.
- **Location is swappable.** Declare FKs with `swapper` and read fields through `get_location_adapter()`, never by importing `Location`.
- **Tests run on SQLite, not MySQL.** `select_for_update()` is ignored (assert the lock is requested) and there are no unsigned columns. `make test` must keep its `-e DJANGO_SETTINGS_MODULE=settings.test`, or tests silently hit MySQL.
- **Tests:** `django.test.TestCase` classes, fixtures from `django_rentals/tests/factories.py` instead of `objects.create()`, and dates built from `localdate()`, never hard-coded.
- **Every change ships to PyPI.** Check public import paths and packaging against a real install and `python -m build` + `twine check`. The version comes from the git tag: tag the merge commit with no `v` prefix, and pushing it publishes.
- **Keep `include-package-data` off** in `pyproject.toml`, or every tracked file lands in the wheel.
- This repo is public: never reference a private consuming project's code or paths.

## Where to read more

| Working on | Read |
|---|---|
| Commands, the `make test` settings trap, MySQL opt-in, lint | `docs/development/setup.md` |
| Domain model, swappable Location, services, querysets, admin | `docs/development/architecture.md` |
| `pyproject.toml`, versioning, releases | `docs/development/packaging.md` |
| Public usage, custom Location model | `README.md` |
