from django.db import migrations

from gamification import catalog


def forwards(apps, schema_editor):
    catalog.sync_catalog(apps.get_model("gamification", "Badge"))


class Migration(migrations.Migration):
    dependencies = [("gamification", "0003_badge_catalog")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
