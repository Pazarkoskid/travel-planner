"""Ги внесува беџовите од каталогот (40 градови/предели + достигнувања) и сликите за постоечките."""
from django.db import migrations

from gamification import catalog


def forwards(apps, schema_editor):
    catalog.sync_catalog(apps.get_model("gamification", "Badge"))


class Migration(migrations.Migration):
    dependencies = [("gamification", "0002_badge_art")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
