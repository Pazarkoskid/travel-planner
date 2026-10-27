import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("businesses", "0001_initial"),
        ("destinations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ItineraryDay",
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
                ("day_number", models.PositiveSmallIntegerField()),
                ("date", models.DateField()),
                ("notes", models.CharField(blank=True, max_length=500)),
            ],
            options={
                "ordering": ["day_number"],
            },
        ),
        migrations.CreateModel(
            name="ItineraryItem",
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
                (
                    "source_type",
                    models.CharField(
                        choices=[
                            ("PLACE", "Place"),
                            ("BUSINESS", "Business"),
                            ("MEAL", "Meal"),
                            ("BREAK", "Break"),
                        ],
                        max_length=10,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("order_index", models.PositiveSmallIntegerField()),
                ("travel_minutes_from_prev", models.FloatField(default=0)),
                ("distance_km_from_prev", models.FloatField(default=0)),
                (
                    "est_cost",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                ("reason", models.CharField(blank=True, max_length=500)),
                ("warning", models.CharField(blank=True, max_length=300)),
                (
                    "business",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="businesses.business",
                    ),
                ),
                (
                    "day",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="trips.itineraryday",
                    ),
                ),
                (
                    "place",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="destinations.place",
                    ),
                ),
            ],
            options={
                "ordering": ["order_index"],
            },
        ),
        migrations.CreateModel(
            name="Trip",
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
                ("title", models.CharField(blank=True, max_length=200)),
                ("start_date", models.DateField()),
                ("days", models.PositiveSmallIntegerField()),
                ("guests", models.PositiveSmallIntegerField(default=1)),
                (
                    "budget",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="EUR, вкупно",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("interests", models.JSONField(default=list)),
                (
                    "pace",
                    models.CharField(
                        choices=[
                            ("relaxed", "Бавно"),
                            ("balanced", "Умерено"),
                            ("intense", "Интензивно"),
                        ],
                        default="balanced",
                        max_length=10,
                    ),
                ),
                (
                    "transport",
                    models.CharField(
                        choices=[
                            ("walking", "Пешки"),
                            ("car", "Автомобил"),
                            ("public", "Јавен превоз/такси"),
                            ("bicycle", "Велосипед"),
                        ],
                        default="car",
                        max_length=10,
                    ),
                ),
                (
                    "modifiers",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Измени од „ревизија“ (поевтино, побавно…)",
                    ),
                ),
                ("warnings", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(default="DRAFT", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "accommodation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="businesses.accommodation",
                    ),
                ),
                (
                    "city",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="destinations.city",
                    ),
                ),
                (
                    "must_visit",
                    models.ManyToManyField(
                        blank=True, related_name="+", to="destinations.place"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trips",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="itineraryday",
            name="trip",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="itinerary_days",
                to="trips.trip",
            ),
        ),
        migrations.CreateModel(
            name="AIPlanRun",
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
                ("provider", models.CharField(max_length=40)),
                ("model", models.CharField(blank=True, max_length=80)),
                ("routing_provider", models.CharField(blank=True, max_length=20)),
                ("selected_place_ids", models.JSONField(default=list)),
                ("rejected_ids", models.JSONField(default=list)),
                ("validation_result", models.JSONField(default=dict)),
                ("metrics", models.JSONField(default=dict)),
                ("instructions", models.CharField(blank=True, max_length=500)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "trip",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plan_runs",
                        to="trips.trip",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="itineraryday",
            unique_together={("trip", "day_number")},
        ),
    ]
