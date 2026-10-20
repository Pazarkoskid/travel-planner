from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Reservation(models.Model):
    class ServiceType(models.TextChoices):
        ACCOMMODATION = "ACCOMMODATION", "Сместување"
        RESTAURANT = "RESTAURANT", "Ресторан"
        BOAT_TOUR = "BOAT_TOUR", "Бродска тура"
        TAXI = "TAXI", "Такси"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Чека одговор"
        QUOTED = "QUOTED", "Понудено (такси)"
        ALTERNATIVE_PROPOSED = "ALTERNATIVE_PROPOSED", "Предложен друг термин"
        CONFIRMED = "CONFIRMED", "Потврдено"
        IN_PROGRESS = "IN_PROGRESS", "Во тек"
        COMPLETED = "COMPLETED", "Завршено"
        REJECTED = "REJECTED", "Одбиено"
        CANCELLED = "CANCELLED", "Откажано"

    # Статуси во кои капацитетот е резервиран за корисникот.
    HOLDING = (Status.PENDING, Status.QUOTED, Status.ALTERNATIVE_PROPOSED, Status.CONFIRMED, Status.IN_PROGRESS)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations")
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="reservations")
    service_type = models.CharField(max_length=16, choices=ServiceType.choices)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    guests = models.PositiveSmallIntegerField(default=1)

    # Сместување
    accommodation_unit = models.ForeignKey("businesses.AccommodationUnit", null=True, blank=True, on_delete=models.PROTECT)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    # Бродска тура
    boat_departure = models.ForeignKey("businesses.BoatDeparture", null=True, blank=True, on_delete=models.PROTECT)
    # Ресторан / такси
    reserved_for = models.DateTimeField(null=True, blank=True)
    pickup = models.CharField(max_length=300, blank=True)
    destination = models.CharField(max_length=300, blank=True)

    notes = models.CharField(max_length=500, blank=True)
    business_message = models.CharField(max_length=500, blank=True)
    proposed_datetime = models.DateTimeField(null=True, blank=True)
    quoted_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    # Snapshot на цената во моментот на барањето.
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="EUR")
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-requested_at"]
        constraints = [
            models.CheckConstraint(condition=Q(check_out__isnull=True) | Q(check_out__gt=F("check_in")),
                                   name="checkout_after_checkin"),
            models.UniqueConstraint(fields=["user", "idempotency_key"], condition=Q(idempotency_key__isnull=False),
                                    name="unique_idempotency_key_per_user"),
        ]

    def __str__(self):
        return f"#{self.pk} {self.service_type} {self.status}"

    @property
    def service_end(self):
        """Кога услугата практично завршува (за дозвола за COMPLETED)."""
        from datetime import datetime, time, timedelta

        from django.utils import timezone

        tz = timezone.get_current_timezone()
        if self.check_out:
            return timezone.make_aware(datetime.combine(self.check_out, time(10, 0)), tz)
        if self.boat_departure_id:
            return self.boat_departure.starts_at + timedelta(minutes=self.boat_departure.tour.duration_min)
        return self.reserved_for


class ReservationItem(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=200)
    quantity = models.PositiveSmallIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)


class ReservationStatusHistory(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
