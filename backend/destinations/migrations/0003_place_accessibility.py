from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "destinations",
            "0002_city_image_credit_city_image_url_city_wiki_query_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="place",
            name="accessibility_notes",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="place",
            name="wheelchair",
            field=models.CharField(
                choices=[
                    ("YES", "Пристапно со инвалидска количка"),
                    ("LIMITED", "Делумно пристапно"),
                    ("NO", "Непристапно"),
                    ("UNKNOWN", "Пристапноста не е проверена"),
                ],
                default="UNKNOWN",
                max_length=8,
            ),
        ),
    ]
