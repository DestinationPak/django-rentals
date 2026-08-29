"""
Backfills RentalListing.location from the existing (nullable, blank)
city string, get-or-creating one Location per distinct normalized city
value.

`city` isn't dropped here - this only ever runs unswapped (nothing
could have set DJANGO_RENTALS_LOCATION_MODEL before this migration
introduced the setting), so there's no external authority to reconcile
against yet; that's destipak's own job once it swaps to public.City
(P9.5) and backfills against it (P9.6). A blank/null city is left
unmatched rather than guessed at - flagged in this migration's own
stdout summary, not silently dropped.
"""

from django.db import migrations
from django.utils.text import slugify


def backfill_location(apps, schema_editor):  # pylint:disable=unused-argument
    RentalListing = apps.get_model("django_rentals", "RentalListing")
    Location = apps.get_model("django_rentals", "Location")

    locations_by_slug = {}
    backfilled = 0
    unmatched = 0

    for listing in RentalListing.objects.all():
        city = (listing.city or "").strip()
        if not city:
            unmatched += 1
            continue

        slug = slugify(city)
        location = locations_by_slug.get(slug)
        if location is None:
            location, _ = Location.objects.get_or_create(
                slug=slug, defaults={"name": city}
            )
            locations_by_slug[slug] = location

        listing.location_id = location.pk
        listing.save(update_fields=["location"])
        backfilled += 1

    print(
        f"\nRentalListing location backfill: {backfilled} listing(s) matched to "
        f"{len(locations_by_slug)} distinct Location row(s); {unmatched} listing(s) "
        "had a blank/null city and were left unmatched."
    )


def noop_reverse(apps, schema_editor):  # pylint:disable=unused-argument
    """Leaves the backfilled Location rows/FKs in place - city (the
    source of truth this migrated from) is untouched either way."""


class Migration(migrations.Migration):

    dependencies = [
        ("django_rentals", "0002_add_location"),
    ]

    operations = [
        migrations.RunPython(backfill_location, noop_reverse),
    ]
