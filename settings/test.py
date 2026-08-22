# pylint:disable=all
from settings.common import *

# SQLite in-memory, regardless of what settings.common's consumer-facing
# DATABASES points at - the test suite shouldn't require a running MySQL
# server, and every model/migration here is plain Django ORM with nothing
# MySQL-specific.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
