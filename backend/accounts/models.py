from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        TOURIST = "TOURIST", "Турист"
        BUSINESS = "BUSINESS", "Сопственик/оператор"
        ADMIN = "ADMIN", "Администратор"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.TOURIST)
    bio = models.CharField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    language = models.CharField(max_length=8, default="mk")
    preferences = models.JSONField(default=dict, blank=True)
    is_profile_public = models.BooleanField(default=True)
    favorite_places = models.ManyToManyField("destinations.Place", blank=True, related_name="favorited_by")

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN
