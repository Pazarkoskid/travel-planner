from django.conf import settings
from django.db import models


class Trip(models.Model):
    class Pace(models.TextChoices):
        RELAXED = "relaxed", "Бавно"
        BALANCED = "balanced", "Умерено"
        INTENSE = "intense", "Интензивно"

    class Transport(models.TextChoices):
        WALKING = "walking", "Пешки"
        CAR = "car", "Автомобил"
        PUBLIC = "public", "Јавен превоз/такси"
        BICYCLE = "bicycle", "Велосипед"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trips")
    city = models.ForeignKey("destinations.City", on_delete=models.PROTECT)
    title = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    days = models.PositiveSmallIntegerField()
    guests = models.PositiveSmallIntegerField(default=1)
    budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="EUR, вкупно")
    interests = models.JSONField(default=list)
    pace = models.CharField(max_length=10, choices=Pace.choices, default=Pace.BALANCED)
    transport = models.CharField(max_length=10, choices=Transport.choices, default=Transport.CAR)
    must_visit = models.ManyToManyField("destinations.Place", blank=True, related_name="+")
    accommodation = models.ForeignKey("businesses.Accommodation", null=True, blank=True, on_delete=models.SET_NULL)
    modifiers = models.JSONField(default=dict, blank=True, help_text="Измени од „ревизија“ (поевтино, побавно…)")
    warnings = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=12, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ItineraryDay(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="itinerary_days")
    day_number = models.PositiveSmallIntegerField()
    date = models.DateField()
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["day_number"]
        unique_together = ("trip", "day_number")


class ItineraryItem(models.Model):
    class Source(models.TextChoices):
        PLACE = "PLACE"
        BUSINESS = "BUSINESS"
        MEAL = "MEAL"
        BREAK = "BREAK"

    day = models.ForeignKey(ItineraryDay, on_delete=models.CASCADE, related_name="items")
    place = models.ForeignKey("destinations.Place", null=True, blank=True, on_delete=models.SET_NULL)
    business = models.ForeignKey("businesses.Business", null=True, blank=True, on_delete=models.SET_NULL)
    source_type = models.CharField(max_length=10, choices=Source.choices)
    title = models.CharField(max_length=200)
    start_time = models.TimeField()
    end_time = models.TimeField()
    order_index = models.PositiveSmallIntegerField()
    travel_minutes_from_prev = models.FloatField(default=0)
    distance_km_from_prev = models.FloatField(default=0)
    est_cost = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    warning = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["order_index"]


class AIPlanRun(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="plan_runs")
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=80, blank=True)
    routing_provider = models.CharField(max_length=20, blank=True)
    selected_place_ids = models.JSONField(default=list)
    rejected_ids = models.JSONField(default=list)
    validation_result = models.JSONField(default=dict)
    metrics = models.JSONField(default=dict)
    instructions = models.CharField(max_length=500, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
