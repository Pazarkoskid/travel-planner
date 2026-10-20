from django.conf import settings
from django.db import models
from django.db.models import Q


class Business(models.Model):
    class Type(models.TextChoices):
        ACCOMMODATION = "ACCOMMODATION", "Сместување"
        RESTAURANT = "RESTAURANT", "Ресторан"
        BOAT_TOUR = "BOAT_TOUR", "Бродска тура"
        TAXI = "TAXI", "Такси"

    class Verification(models.TextChoices):
        PENDING = "PENDING", "Чека одобрување"
        APPROVED = "APPROVED", "Одобрен"
        REJECTED = "REJECTED", "Одбиен"
        SUSPENDED = "SUSPENDED", "Суспендиран"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owned_businesses")
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=16, choices=Type.choices)
    description = models.TextField(blank=True)
    city = models.ForeignKey("destinations.City", on_delete=models.PROTECT, related_name="businesses")
    address = models.CharField(max_length=300, blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    image_url = models.URLField(blank=True, max_length=600)
    verification_status = models.CharField(max_length=12, choices=Verification.choices, default=Verification.PENDING)
    is_sponsored = models.BooleanField(default=False, help_text="Секогаш се прикажува со ознака „Спонзорирано“.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "businesses"

    def __str__(self):
        return self.name

    def can_manage(self, user):
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == "ADMIN" or self.owner_id == user.id:
            return True
        return self.members.filter(user=user).exists()


class BusinessUser(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_memberships")
    permission_role = models.CharField(max_length=16, choices=[("OWNER", "Сопственик"), ("STAFF", "Вработен")], default="STAFF")

    class Meta:
        unique_together = ("business", "user")


def managed_businesses(user):
    if user.is_superuser or user.role == "ADMIN":
        return Business.objects.all()
    return Business.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()


class Accommodation(models.Model):
    class PropertyType(models.TextChoices):
        ROOM = "ROOM", "Соба"
        STUDIO = "STUDIO", "Студио"
        APARTMENT = "APARTMENT", "Апартман"
        HOUSE = "HOUSE", "Цел објект"

    AMENITIES = ("wifi", "ac", "parking", "kitchen", "terrace", "lake_view", "accessible", "pets")

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="accommodations")
    title = models.CharField(max_length=200)
    property_type = models.CharField(max_length=12, choices=PropertyType.choices)
    description = models.TextField(blank=True)
    max_guests = models.PositiveSmallIntegerField()
    bedrooms = models.PositiveSmallIntegerField(default=1)
    beds = models.PositiveSmallIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True)
    rules = models.TextField(blank=True)
    cleaning_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    free_cancellation_days = models.PositiveSmallIntegerField(default=2)
    image_url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class AccommodationUnit(models.Model):
    """Еден тип/единица. Повеќе идентични соби = available_units > 1 во достапноста."""

    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE, related_name="units")
    unit_name = models.CharField(max_length=120)

    def __str__(self):
        return f"{self.accommodation} — {self.unit_name}"


class AccommodationAvailability(models.Model):
    unit = models.ForeignKey(AccommodationUnit, on_delete=models.CASCADE, related_name="availability")
    date = models.DateField()
    available_units = models.PositiveSmallIntegerField(default=1)
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ("unit", "date")
        ordering = ["date"]


class RestaurantProfile(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="restaurant")
    opening_hours = models.JSONField(default=dict, blank=True, help_text='{"mon": ["10:00", "23:00"], ...}')
    menu = models.JSONField(default=list, blank=True, help_text='[{"name": "...", "price": 8.5}]')
    price_range = models.CharField(max_length=8, blank=True, help_text="€, €€, €€€")
    cuisine = models.CharField(max_length=120, blank=True)
    max_party_size = models.PositiveSmallIntegerField(default=12)


class BoatTour(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="boat_tours")
    title = models.CharField(max_length=200)
    route = models.TextField()
    description = models.TextField(blank=True)
    # [{"name": "...", "minutes": 0, "stop_min": 0, "lat": 41.1, "lng": 20.8, "note": "..."}]
    stops = models.JSONField(default=list, blank=True, help_text="Постојки по редослед, со минути од поаѓање")
    includes = models.TextField(blank=True, help_text="Што е вклучено во цената")
    duration_min = models.PositiveIntegerField()
    price_per_person = models.DecimalField(max_digits=8, decimal_places=2)
    departure_point = models.CharField(max_length=200)
    rules = models.TextField(blank=True)

    def __str__(self):
        return self.title


class BoatDeparture(models.Model):
    tour = models.ForeignKey(BoatTour, on_delete=models.CASCADE, related_name="departures")
    starts_at = models.DateTimeField(db_index=True)
    capacity = models.PositiveSmallIntegerField()
    reserved_seats = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=[("SCHEDULED", "Закажано"), ("CANCELLED", "Откажано")], default="SCHEDULED")

    class Meta:
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(condition=Q(reserved_seats__lte=models.F("capacity")), name="departure_not_overbooked"),
        ]

    @property
    def remaining_seats(self):
        return self.capacity - self.reserved_seats


class TaxiService(models.Model):
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name="taxi")
    service_area = models.CharField(max_length=200)
    passenger_capacity = models.PositiveSmallIntegerField(default=4)
    base_fare = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    per_km = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    available_24h = models.BooleanField(default=False)
    vehicles = models.CharField(max_length=200, blank=True)
    languages = models.CharField(max_length=120, blank=True)
    fare_info = models.TextField(blank=True, help_text="Фиксни релации, доплати, начин на плаќање")
