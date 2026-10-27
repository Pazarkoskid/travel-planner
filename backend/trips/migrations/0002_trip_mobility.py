from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trips", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="trip",
            name="mobility",
            field=models.CharField(
                choices=[
                    ("standard", "Без посебни потреби"),
                    ("reduced", "Намалена подвижност (без стрмни скали)"),
                    ("wheelchair", "Инвалидска количка"),
                ],
                default="standard",
                max_length=10,
            ),
        ),
    ]
