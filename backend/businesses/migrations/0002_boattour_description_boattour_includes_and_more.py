from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("businesses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="boattour",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="boattour",
            name="includes",
            field=models.TextField(blank=True, help_text="Што е вклучено во цената"),
        ),
        migrations.AddField(
            model_name="boattour",
            name="stops",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Постојки по редослед, со минути од поаѓање",
            ),
        ),
        migrations.AddField(
            model_name="business",
            name="website",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="restaurantprofile",
            name="cuisine",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="taxiservice",
            name="available_24h",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="taxiservice",
            name="fare_info",
            field=models.TextField(
                blank=True, help_text="Фиксни релации, доплати, начин на плаќање"
            ),
        ),
        migrations.AddField(
            model_name="taxiservice",
            name="languages",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="taxiservice",
            name="vehicles",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AlterField(
            model_name="business",
            name="image_url",
            field=models.URLField(blank=True, max_length=600),
        ),
    ]
