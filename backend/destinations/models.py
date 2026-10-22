from django.db import models


class City(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    region = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    center_lat = models.FloatField()
    center_lng = models.FloatField()
    image_url = models.URLField(blank=True, max_length=600)
    image_credit = models.CharField(max_length=300, blank=True, help_text="Автор и лиценца на фотографијата")
    wiki_query = models.CharField(max_length=200, blank=True, help_text="Поим за пребарување слика на Wikipedia")

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cities"

    def __str__(self):
        return self.name


class Place(models.Model):
    class Category(models.TextChoices):
        HISTORY = "HISTORY", "Историја"
        RELIGIOUS = "RELIGIOUS", "Цркви и манастири"
        MUSEUM = "MUSEUM", "Музеј"
        NATURE = "NATURE", "Природа"
        VIEWPOINT = "VIEWPOINT", "Видиковец"
        BEACH = "BEACH", "Плажа"
        CULTURE = "CULTURE", "Култура"
        FOOD = "FOOD", "Локална храна"
        ACTIVITY = "ACTIVITY", "Активност"

    class Wheelchair(models.TextChoices):
        YES = "YES", "Пристапно со инвалидска количка"
        LIMITED = "LIMITED", "Делумно пристапно"
        NO = "NO", "Непристапно"
        UNKNOWN = "UNKNOWN", "Пристапноста не е проверена"

    class Status(models.TextChoices):
        VERIFIED = "VERIFIED", "Проверено"
        UNVERIFIED = "UNVERIFIED", "Непроверено"
        ARCHIVED = "ARCHIVED", "Архивирано"

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="places")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    category = models.CharField(max_length=16, choices=Category.choices)
    description = models.TextField(blank=True)
    lat = models.FloatField(db_index=True)
    lng = models.FloatField(db_index=True)
    visit_duration_min = models.PositiveIntegerField(default=60)
    # Цена и работно време се null кога не се проверени — никогаш не се измислуваат.
    price_eur = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    source = models.CharField(max_length=300, help_text="Извор на податоците")
    verified_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UNVERIFIED)
    # Официјална листа знаменитости за „Град 100%“ — ја одржува администраторот.
    is_required_landmark = models.BooleanField(default=False)
    checkin_radius_m = models.PositiveIntegerField(default=300)
    image_url = models.URLField(blank=True, max_length=600)
    image_credit = models.CharField(max_length=300, blank=True, help_text="Автор и лиценца на фотографијата")
    wiki_query = models.CharField(max_length=200, blank=True, help_text="Поим за пребарување слика на Wikipedia")
    # Пристапност за лица со попреченост (OSM: wheelchair=yes/limited/no).
    wheelchair = models.CharField(max_length=8, choices=Wheelchair.choices, default=Wheelchair.UNKNOWN)
    accessibility_notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["city", "name"]
        unique_together = ("city", "slug")

    def __str__(self):
        return f"{self.name} ({self.city})"
