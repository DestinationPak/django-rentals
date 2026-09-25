# Local development

All development happens inside Docker; there is no supported bare-metal workflow. The importable app is `src/django_rentals/`; `devsite/` is a throwaway Django project shell (`urls.py`/`wsgi.py`/`asgi.py`) used only for local dev and not part of the published package.

## Commands

```bash
make build          # docker compose build (destroys existing containers first)
make dev.up         # start web (SQLite by default, see Settings below for MySQL)
make shell          # a shell inside the web container
make update_db      # run migrations
make random_rentals  # seed random operators/listings (generate_rentals --batch_size=100)
make test           # run pytest on in-memory SQLite
make stop / make destroy  # stop / tear down containers (destroy removes volumes)
make logs           # tail web container logs
```

Run a single test inside the container (`make shell`):

```bash
pytest django_rentals/tests/test_services.py
pytest django_rentals/tests/test_services.py::SomeTestCase::test_name
```

## Why `make test` passes `-e DJANGO_SETTINGS_MODULE`

`make test` runs `docker compose run --rm --no-deps -e DJANGO_SETTINGS_MODULE=settings.test web pytest`. The `web` service sets `DJANGO_SETTINGS_MODULE=settings.common` for the whole container, and pytest-django only uses `pytest.ini`'s value as a fallback (`os.environ.setdefault`). Without the explicit `-e`, tests silently run against real MySQL, and `--no-deps` (skip starting the database) becomes unsafe.

`settings.test` imports `settings.common` and swaps `DATABASES` to in-memory SQLite. With `--no-migrations`, tests build the schema straight from models, so tests pick up model changes without a migration. Still create the migration for real deployments.

SQLite differs from MySQL in ways tests won't catch: it ignores `select_for_update()` (so a lock is tested by asserting it is requested), and it has no unsigned columns (so a subtraction that goes below zero only fails on MySQL).

## Tests

- Write tests as `django.test.TestCase` subclasses, one class per model or concern, not bare `@pytest.mark.django_db` functions.
- Build fixtures with `django_rentals/tests/factories.py` (`RentalOperatorFactory`, `RentalListingFactory`, `RentalAvailabilityFactory`, `RentalBookingFactory`, `UserFactory`), not `Model.objects.create(...)`. A raw `create()` is fine when the test is about model/manager mechanics (slug or booking-number generation, an `.active()` filter).
- Build dates from `localdate()`, never hard-code them: `open()` and `bookable()` leave out past dates, so a fixed date turns into a failing test once it passes.

## Linting

`python run_lint.py` runs pylint over the package and fails below the `THRESHOLD` in `run_lint.py`.

## Settings

`settings/common.py` is the real settings module (Docker sets `DJANGO_SETTINGS_MODULE=settings.common`); `settings/test.py` re-exports it with SQLite.

`DATABASES` reads `DATABASE_ENGINE`, defaulting to SQLite, the same pattern django-oscar and wagtail use. MySQL is opt-in and needs both:

- the compose profile: `docker compose --profile mysql up` (the `database` service has `profiles: [mysql]`), and
- `DATABASE_ENGINE=django.db.backends.mysql` in `.env`.

`mysqlclient` is installed by its own `RUN pip install` in the `Dockerfile`, not as a project dependency, so it stays out of the dependency graph and Dependabot; it's dev-only.

`web` has no `depends_on: database` health gate (Compose can't depend on a profile-gated service that isn't active). On a fresh MySQL opt-in, `web`'s first `migrate` can race MySQL's startup and fail once; `restart: unless-stopped` retries it within seconds.
