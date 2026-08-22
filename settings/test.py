# pylint:disable=all
from settings.common import *

# In-memory SQLite - nothing here is MySQL-specific, and tests shouldn't need a running MySQL server.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
