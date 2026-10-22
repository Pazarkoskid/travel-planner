"""Повторна синхронизација на каталогот: слики за печатите на знаменитостите (stamp-*.webp).

Потребна е бидејќи 0003 можеби веќе се извршила со постара верзија на каталогот,
а `recompute_badges` не мора да е во build командата.
"""
from django.db import migrations

from gamification import catalog


def forwards(apps, schema_editor):
    catalog.sync_catalog(apps.get_model("gamification", "Badge"))


class Migration(migrations.Migration):
    dependencies = [("gamification", "0003_badge_catalog")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
