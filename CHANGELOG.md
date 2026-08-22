# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- CI's `Unit Tests` workflow now actually runs `pytest` - its last step was a
  copy-paste of the `Quality` workflow's lint command, so no test in the
  suite ever ran on pull requests.
- `setup.py`/`setup.cfg` no longer duplicate (and drift from) each other's
  package metadata; `setup.cfg` is now the single source of truth.
- Published `install_requires` now actually matches the code's imports:
  adds `djangorestframework`, `django-filter`, and `drf-spectacular` (all
  imported by the app but missing from `0.1.0`'s metadata beyond what
  `setup.py`'s `requirements.txt`-derived list already carried), drops
  `mysqlclient`/`setuptools`/`Pillow` (none of the three is imported by
  this package - `RentalImage.image` is a plain `URLField`, not an
  `ImageField`).
- `packages = find:` no longer sweeps the dev-only `django-rentals` project
  shell and local `settings` package into the built wheel/sdist alongside
  the real `django_rentals` app.
- `LICENSE` no longer attributes the project to "The Python Packaging
  Authority" (leftover cookiecutter boilerplate).

### Changed
- Local dev/test settings (`settings/test.py`) now default to an in-memory
  SQLite database instead of requiring a running MySQL server - nothing in
  this package's models/migrations is MySQL-specific. `settings/common.py`
  (Docker/local-server dev) is unaffected and still targets MySQL.
- CI now runs the suite across a Python 3.11/3.12/3.13 x Django 4.2/5.2
  matrix instead of a single pinned combination.
- `django-filter` is capped at `<25.2` (25.2 dropped Django 4.2 support) so
  the declared `Django>=4.2,<6.0` support range is one that's actually
  installable and tested, not just asserted.

## [0.1.0]
Initial release: rental operator/listing/availability/booking models, a
public read-only catalog API, guest booking create/lookup, and a
swappable `Location` model.
