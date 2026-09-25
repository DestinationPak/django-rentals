# Architecture

django-rentals ships models, querysets, business rules (`services.py`) and admin for rental operators, listings, availability and bookings: vehicle and gear rentals such as jeep tours and trekking equipment. It has no API, views or URLs (the DRF API was removed in 1.0.0): each project builds its own endpoints on the services and querysets. It is a sibling of [django-trips](https://github.com/DestinationPak/django-trips) and follows the same structure.

Not built yet: reviews.

## Domain model

Everything hangs off `RentalListing` (`django_rentals/models.py`).

- `RentalListing` → `RentalOperator`, the owning business (like `django_trips.Host`), a plain domain model with no login fields.
- `RentalListing` → `RentalAvailability` (one bookable date with `units_available`, like `TripSchedule`) → `RentalBooking` (like `TripBooking`, but for a `start_date`/`end_date` range instead of one departure date).
- There is no tier or package model like `TripPackage`: a separate `RentalListing` per vehicle or kit already does that job. Don't add one without a real product reason.
- `RentalBooking.generate_booking_number()` works like `TripBooking`'s (zero-padded count plus 2 random digits) with a `DPR` prefix instead of `DPT`, so references are easy to tell apart.

## No ownership or permissions here

The package has no idea who may manage a `RentalOperator`: no membership model, no permission classes, no auth. That layer belongs to the project that installs the app, the same split django-trips uses. Don't add auth, permission or membership code here.

## Location is swappable

`Location` has plain `name`/`slug`/`lat`/`lng` and no hierarchy (unlike django-trips' `type`/`parent`). It is swappable via `swapper` (see the README's "Custom Location model"), like django-trips and django-hotels.

- `RentalListing.location` (nullable FK) is the only location field. The old free-text `RentalListing.city` was backfilled into it (`0003_backfill_location_from_city.py`) and dropped (`0004_remove_rentallisting_city.py`).
- Consumers read location fields through `django_rentals/location_adapter.py` (`get_location_adapter()`, `DJANGO_RENTALS_LOCATION_ADAPTER`).
- `AbstractLocation` (`models.py`) is a plain abstract model (like `AbstractUser`) that an installer can inherit instead of writing a `LocationAdapter` subclass.

## Business rules

Writes live in `services.py` and reads in the querysets in `managers.py`, so every consumer's API, command or admin action behaves the same.

- `create_rental_booking()` books a listing from `start_date` to `end_date`, both days included:
  - `validate_rental_dates()` refuses a range that ends before it starts, and `availability` must be the row for `start_date`.
  - Under a row lock, every day in the range needs an `open()` row with a unit left; missing days are listed in the error.
  - Each of those rows gives up one unit, and the price is `availability`'s per-day price times the number of days.
- `cancel_rental_booking()` refuses an already cancelled booking and, unless `check_cancellable=False` (staff tools), one whose status no longer allows cancelling. It gives one unit back on each day the booking covered.
- `delete_rental_booking()` gives the units back unless the booking was already cancelled, then deletes it.
- A rule failure raises Django's `ValidationError`, keyed by field where there is one (`availability` for the day checks), for the consumer's API to turn into its own error response.

Read side:

- `RentalListing.objects.published()`: published, active, operator verified.
- `RentalAvailability.objects.open()`: dates a guest may book whether or not units are left (today onwards, on a published listing). `bookable()` is `open()` with a unit left, earliest first.
- `RentalBooking.objects.matching_guest(number, email=...)`: the guest lookup, never on `number` alone.

## Admin

The admin goes through the same services: setting a booking to cancelled calls `cancel_rental_booking()`, deleting one (singly or in bulk) calls `delete_rental_booking()`, a cancelled booking can't be reopened (`REOPEN_NOT_ALLOWED`), and a booking's `availability`, `start_date` and `end_date` are read-only once it exists, since changing them would leave unit counts wrong.
