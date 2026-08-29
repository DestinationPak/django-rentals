from django.db import models
from django.utils.timezone import now


class ActiveQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class RentalOperatorQuerySet(ActiveQuerySet):
    def active(self):
        return super().active().filter(verified=True)


class RentalListingQuerySet(ActiveQuerySet):
    def active(self):
        return super().active().filter(operator__verified=True)


class RentalAvailabilityQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(date__gte=now())
