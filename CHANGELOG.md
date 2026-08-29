# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed
- Migrated packaging from `setup.py`/`setup.cfg`/`MANIFEST.in` to a single
  `pyproject.toml` (PEP 621), and moved the importable app to `src/
  django_rentals/` (the throwaway dev project shell is now `devsite/`,
  renamed from `django-rentals/` to stop the two from being confused with
  each other or with the published package).
- `__version__` is now derived from the git tag at build time via
  `setuptools-scm`, instead of being a hand-maintained string in
  `__init__.py` that the release workflow patched with `sed`. The release
  workflow now fails outright if the tag doesn't match the version
  setuptools-scm computes, rather than silently patching around a mismatch.
- Runtime and dev dependencies are declared once, in `pyproject.toml`
  (`[project.dependencies]` / `[project.optional-dependencies] dev`/`docs`)
  - `requirements.txt`/`requirements-dev.txt` are gone, and CI/Docker both
    install via `pip install -e ".[dev]"` instead. Dropped `ddt` from the
    dev dependency list - nothing in the test suite imports it.
- `.dockerignore` was leftover Node/JS cookiecutter boilerplate
  (`node_modules`, `.eslintrc.json`, `.npmignore`, `commitlint.config.js`)
  that also excluded `README.md`/`LICENSE` from the build context - broken
  now that `pyproject.toml` needs both present to build package metadata.
  Replaced with a Python-appropriate ignore list.

### Fixed
- The `Quality` CI workflow's pylint step (`python -m run_lint.py`) was
  invalid syntax - `-m` takes a module name, not a filename, so it raised
  `ModuleNotFoundError` on every run and pylint never actually executed.
- `run_lint.py` was passing all of its pylint flags as one joined string
  instead of separate list items, so `--load-plugins pylint_django` and
  `--django-settings-module` were silently never applied - Django-specific
  lint checks have never actually been active.
- `.pylintrc` set `suggestion-mode`, an option pylint 4.x removed; every
  lint run errored on an unrecognized option.
- `[tool.setuptools.packages.find]`'s `exclude` alone doesn't stop
  PEP 621's default `include-package-data = true` (combined with
  setuptools-scm's git-file-finder) from sweeping every git-tracked file
  under a found package's directory tree into the wheel as package data -
  `django_rentals.api.tests` (this package's own internal API test suite,
  not documented as consumer-facing) would otherwise leak into the built
  wheel despite being listed under `exclude`. `include-package-data` is
  now explicitly disabled; `django_rentals.tests` (the factories module,
  which *is* documented as consumer-facing) still ships as intended.
- Removed the `Makefile`'s `publish.test`/`publish.prod` targets - a
  second, local release path that both duplicated `release.yaml`'s CI
  pipeline via a deprecated `setup.py sdist bdist_wheel` invocation and
  bypassed its version-gate and PyPI Trusted Publishing (OIDC) entirely in
  favor of a locally-stored token. It also predated the `src/` layout
  migration and would have deleted the real package (`rm -rf
  src/django_rentals`) if run today.

### Added
- `pyproject.toml`'s `docs` extra (`sphinx`, `myst-parser`, `furo`) and a
  `docs/` Sphinx scaffold, publishable to Read the Docs.
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant), and
  `SECURITY.md` (vulnerability disclosure process).
- A `Development Status :: 3 - Alpha` classifier - previously absent
  entirely, despite being one of the most visible fields on a package's
  PyPI page.

## [0.3.0] - 2026-08-29

### Added
- `AbstractLocation`, split out of `Location` so a consumer building a
  brand-new custom Location model can inherit it directly instead of
  writing a `LocationAdapter` subclass.
- `DATABASES` is now configurable via a `DATABASE_ENGINE` env var
  (defaulting to SQLite), matching the pattern well-known reusable Django
  apps (django-oscar, wagtail) use. `docker-compose.yml`'s `database`
  (MySQL) service is now behind a `mysql` Compose profile, so `make
  dev.up` runs against SQLite with no MySQL container at all unless
  explicitly opted into.

### Removed
- `RentalListing.city` (the original free-text location `CharField`), now
  that `RentalListing.location` is fully wired up. A prior migration
  best-effort backfilled `location` from `city` by name before this field
  was dropped.

### Fixed
- `make test` was silently running against real MySQL instead of SQLite -
  `settings/test.py` swaps in an in-memory SQLite `DATABASES`, but
  `docker-compose.yml`'s `web` service set `DJANGO_SETTINGS_MODULE` as a
  container-wide env var, which pytest-django only uses as a fallback
  (`os.environ.setdefault`) and therefore never actually overrode.
- `django-filter` requirement widened from `<25.2,>=23.2` to `>=26.1,<26.2`.

## [0.2.0]

### Added
- Availability search endpoint, filterable by `?listing=`, `?date_from=`,
  `?date_to=` in any combination.
- Guest booking lookup hardening, plus authenticated booking
  retrieve/update/cancel.
- Quality tooling (pylint/isort/pre-commit) brought to parity with
  `django-trips`/`django-hotels`.

### Fixed
- CI's `Unit Tests` workflow now actually runs `pytest` - its last step was
  a copy-paste of the `Quality` workflow's lint command, so no test in the
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

## [0.1.0]
Initial release: rental operator/listing/availability/booking models, a
public read-only catalog API, guest booking create/lookup, and a
swappable `Location` model.
