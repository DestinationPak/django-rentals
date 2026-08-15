"""
Seeds random rental operators/listings/availability for local dev.

EXAMPLE USAGE:
    ./manage.py generate_rentals --batch_size=20
"""

import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from django_rentals.choices import RentalCategory
from django_rentals.models import RentalAvailability, RentalListing, RentalOperator

fake = Faker()
User = get_user_model()

DEFAULT_SETTINGS = {
    "RENTAL_OPERATORS": ["Sample Rentals Co"],
    "RENTAL_CITIES": ["Skardu", "Hunza"],
}


class Command(BaseCommand):
    """Generates a batch of random rental operators/listings/availability."""

    help = "Generate random rental operators, listings, and availability."

    def add_arguments(self, parser):
        parser.add_argument("--batch_size", type=int, default=20)

    def handle(self, *args, **options):
        use_defaults = getattr(settings, "USE_DEFAULT_RENTALS", True)
        operator_names = getattr(
            settings,
            "RENTAL_OPERATORS",
            DEFAULT_SETTINGS["RENTAL_OPERATORS"],
        ) if not use_defaults else DEFAULT_SETTINGS["RENTAL_OPERATORS"]
        cities = getattr(
            settings, "RENTAL_CITIES", DEFAULT_SETTINGS["RENTAL_CITIES"]
        ) if not use_defaults else DEFAULT_SETTINGS["RENTAL_CITIES"]

        creator, _ = User.objects.get_or_create(
            username="rentals-seed-bot", defaults={"email": "seed@example.com"}
        )

        operators = []
        for name in operator_names:
            operator, _ = RentalOperator.objects.get_or_create(
                name=name,
                defaults={
                    "slug": slugify(name),
                    "verified": True,
                    "email": fake.company_email(),
                },
            )
            operators.append(operator)

        batch_size = options["batch_size"]
        created = 0
        for _ in range(batch_size):
            operator = random.choice(operators)
            category = random.choice(list(RentalCategory.values))
            name = (
                f"{fake.word().title()} {'4x4' if category == RentalCategory.VEHICLE else 'Kit'}"
            )
            listing = RentalListing.objects.create(
                name=name,
                slug=f"{slugify(name)}-{random.randint(1000, 9999)}",
                operator=operator,
                category=category,
                city=random.choice(cities),
                description=fake.paragraph(),
                price_per_day=random.randint(20, 200) * 100,
                created_by=creator,
            )
            for offset in range(1, 8):
                RentalAvailability.objects.create(
                    listing=listing,
                    date=timezone.now().date() + timedelta(days=offset),
                    units_available=random.randint(1, 5),
                )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} rental listings."))
