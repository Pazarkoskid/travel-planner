import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("destinations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Badge",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(blank=True, max_length=300)),
                (
                    "kind",
                    models.CharField(
                        choices=[("PLACE", "Беџ за место"), ("LEVEL", "Ниво")],
                        max_length=8,
                    ),
                ),
                (
                    "level",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("EXPLORER", "Истражувач"),
                            ("LOCAL_ADVENTURER", "Локален авантурист"),
                            ("CITY_EXPLORER", "Градски истражувач"),
                            ("CITY_MASTER", "Мајстор на градот"),
                            ("MACEDONIA_EXPLORER", "Истражувач на Македонија"),
                        ],
                        max_length=24,
                    ),
                ),
                ("icon", models.CharField(default="🏅", max_length=8)),
                (
                    "city",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="badges",
                        to="destinations.city",
                    ),
                ),
                (
                    "place",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="badges",
                        to="destinations.place",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PhotoCheckIn",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("image", models.ImageField(upload_to="checkins/%Y/%m/")),
                ("image_sha256", models.CharField(db_index=True, max_length=64)),
                ("client_lat", models.FloatField(blank=True, null=True)),
                ("client_lng", models.FloatField(blank=True, null=True)),
                ("exif_lat", models.FloatField(blank=True, null=True)),
                ("exif_lng", models.FloatField(blank=True, null=True)),
                ("taken_at", models.DateTimeField(blank=True, null=True)),
                ("distance_m", models.FloatField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Чека проверка"),
                            ("APPROVED", "Одобрено"),
                            ("REJECTED", "Одбиено"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=10,
                    ),
                ),
                ("verification_notes", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "place",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkins",
                        to="destinations.place",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_checkins",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="checkins",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="PlacePhoto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("caption", models.CharField(blank=True, max_length=300)),
                ("is_public", models.BooleanField(default=True)),
                (
                    "is_hidden",
                    models.BooleanField(
                        default=False, help_text="Скриено од модератор"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "checkin",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photo",
                        to="gamification.photocheckin",
                    ),
                ),
                (
                    "place",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="destinations.place",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="place_photos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CityAchievement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("documented_required", models.PositiveIntegerField(default=0)),
                ("required_total", models.PositiveIntegerField(default=0)),
                ("documented_any", models.PositiveIntegerField(default=0)),
                ("percent", models.FloatField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "city",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="destinations.city",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="city_achievements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "city")},
            },
        ),
        migrations.CreateModel(
            name="PlaceReport",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("reason", models.CharField(max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("OPEN", "Отворено"),
                            ("RESOLVED", "Решено"),
                            ("DISMISSED", "Отфрлено"),
                        ],
                        default="OPEN",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "moderator",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="moderated_place_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "photo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reports",
                        to="gamification.placephoto",
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("photo", "reporter")},
            },
        ),
        migrations.CreateModel(
            name="UserBadge",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("unlocked_at", models.DateTimeField(auto_now_add=True)),
                (
                    "badge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="holders",
                        to="gamification.badge",
                    ),
                ),
                (
                    "source_checkin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="gamification.photocheckin",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_badges",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-unlocked_at"],
                "unique_together": {("user", "badge")},
            },
        ),
    ]
