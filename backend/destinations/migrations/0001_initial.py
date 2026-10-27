import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="City",
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
                ("name", models.CharField(max_length=100)),
                ("slug", models.SlugField(unique=True)),
                ("region", models.CharField(blank=True, max_length=100)),
                ("description", models.TextField(blank=True)),
                ("center_lat", models.FloatField()),
                ("center_lng", models.FloatField()),
            ],
            options={
                "verbose_name_plural": "cities",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Place",
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
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=220)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("HISTORY", "Историја"),
                            ("RELIGIOUS", "Цркви и манастири"),
                            ("MUSEUM", "Музеј"),
                            ("NATURE", "Природа"),
                            ("VIEWPOINT", "Видиковец"),
                            ("BEACH", "Плажа"),
                            ("CULTURE", "Култура"),
                            ("FOOD", "Локална храна"),
                            ("ACTIVITY", "Активност"),
                        ],
                        max_length=16,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("lat", models.FloatField(db_index=True)),
                ("lng", models.FloatField(db_index=True)),
                ("visit_duration_min", models.PositiveIntegerField(default=60)),
                (
                    "price_eur",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                ("opening_time", models.TimeField(blank=True, null=True)),
                ("closing_time", models.TimeField(blank=True, null=True)),
                (
                    "source",
                    models.CharField(help_text="Извор на податоците", max_length=300),
                ),
                ("verified_at", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("VERIFIED", "Проверено"),
                            ("UNVERIFIED", "Непроверено"),
                            ("ARCHIVED", "Архивирано"),
                        ],
                        default="UNVERIFIED",
                        max_length=12,
                    ),
                ),
                ("is_required_landmark", models.BooleanField(default=False)),
                ("checkin_radius_m", models.PositiveIntegerField(default=300)),
                ("image_url", models.URLField(blank=True)),
                (
                    "city",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="places",
                        to="destinations.city",
                    ),
                ),
            ],
            options={
                "ordering": ["city", "name"],
                "unique_together": {("city", "slug")},
            },
        ),
    ]
