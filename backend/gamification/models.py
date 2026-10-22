from django.conf import settings
from django.db import models


class Badge(models.Model):
    class Kind(models.TextChoices):
        PLACE = "PLACE", "Беџ за место"
        LEVEL = "LEVEL", "Ниво"
        REGION = "REGION", "Град или предел"
        CATEGORY = "CATEGORY", "Достигнување"

    class Level(models.TextChoices):
        EXPLORER = "EXPLORER", "Истражувач"
        LOCAL_ADVENTURER = "LOCAL_ADVENTURER", "Локален авантурист"
        CITY_EXPLORER = "CITY_EXPLORER", "Градски истражувач"
        CITY_MASTER = "CITY_MASTER", "Мајстор на градот"
        MACEDONIA_EXPLORER = "MACEDONIA_EXPLORER", "Истражувач на Македонија"

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    level = models.CharField(max_length=24, choices=Level.choices, blank=True)
    place = models.ForeignKey("destinations.Place", null=True, blank=True, on_delete=models.CASCADE, related_name="badges")
    city = models.ForeignKey("destinations.City", null=True, blank=True, on_delete=models.CASCADE, related_name="badges")
    icon = models.CharField(max_length=8, default="🏅")
    art = models.CharField(max_length=200, blank=True, help_text="Слика од frontend, пр. /badges/loc-02-ohrid.webp")
    rule = models.JSONField(default=dict, blank=True, help_text="Правило за REGION/CATEGORY (види gamification/catalog.py)")
    available = models.BooleanField(default=True, help_text="False = прикажан како „наскоро“, не може да се освои")
    sort = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort", "name"]

    def __str__(self):
        return self.name


class PhotoCheckIn(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Чека проверка"
        APPROVED = "APPROVED", "Одобрено"
        REJECTED = "REJECTED", "Одбиено"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="checkins")
    place = models.ForeignKey("destinations.Place", on_delete=models.CASCADE, related_name="checkins")
    image = models.ImageField(upload_to="checkins/%Y/%m/")
    image_sha256 = models.CharField(max_length=64, db_index=True)
    client_lat = models.FloatField(null=True, blank=True)
    client_lng = models.FloatField(null=True, blank=True)
    exif_lat = models.FloatField(null=True, blank=True)
    exif_lng = models.FloatField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    distance_m = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    verification_notes = models.JSONField(default=list, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="reviewed_checkins")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PlacePhoto(models.Model):
    """Фотографијата во галеријата на местото; секогаш поврзана со корисникот."""

    checkin = models.OneToOneField(PhotoCheckIn, on_delete=models.CASCADE, related_name="photo")
    place = models.ForeignKey("destinations.Place", on_delete=models.CASCADE, related_name="photos")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="place_photos")
    caption = models.CharField(max_length=300, blank=True)
    is_public = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False, help_text="Скриено од модератор")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class UserBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="holders")
    unlocked_at = models.DateTimeField(auto_now_add=True)
    source_checkin = models.ForeignKey(PhotoCheckIn, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("user", "badge")  # беџот се доделува еднаш
        ordering = ["-unlocked_at"]


class CityAchievement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="city_achievements")
    city = models.ForeignKey("destinations.City", on_delete=models.CASCADE)
    documented_required = models.PositiveIntegerField(default=0)
    required_total = models.PositiveIntegerField(default=0)
    documented_any = models.PositiveIntegerField(default=0)
    percent = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "city")


class PlaceReport(models.Model):
    photo = models.ForeignKey(PlacePhoto, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=[("OPEN", "Отворено"), ("RESOLVED", "Решено"),
                                                      ("DISMISSED", "Отфрлено")], default="OPEN")
    moderator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="moderated_place_reports")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("photo", "reporter")


class PhotoLike(models.Model):
    """Лајк на фотографија од галеријата; еден корисник — еден лајк по фотографија."""

    photo = models.ForeignKey(PlacePhoto, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="photo_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["photo", "user"], name="unique_photo_like")]
