from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("destinations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="city",
            name="image_credit",
            field=models.CharField(
                blank=True, help_text="Автор и лиценца на фотографијата", max_length=300
            ),
        ),
        migrations.AddField(
            model_name="city",
            name="image_url",
            field=models.URLField(blank=True, max_length=600),
        ),
        migrations.AddField(
            model_name="city",
            name="wiki_query",
            field=models.CharField(
                blank=True,
                help_text="Поим за пребарување слика на Wikipedia",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="place",
            name="image_credit",
            field=models.CharField(
                blank=True, help_text="Автор и лиценца на фотографијата", max_length=300
            ),
        ),
        migrations.AddField(
            model_name="place",
            name="wiki_query",
            field=models.CharField(
                blank=True,
                help_text="Поим за пребарување слика на Wikipedia",
                max_length=200,
            ),
        ),
        migrations.AlterField(
            model_name="place",
            name="image_url",
            field=models.URLField(blank=True, max_length=600),
        ),
    ]
