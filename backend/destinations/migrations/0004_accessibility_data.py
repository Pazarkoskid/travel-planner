"""Почетни (проценети) податоци за пристапност на демо местата; менува само „непознато“."""
from django.db import migrations

from destinations import accessibility_data


def forwards(apps, schema_editor):
    accessibility_data.apply(apps.get_model("destinations", "Place"))


class Migration(migrations.Migration):
    dependencies = [("destinations", "0003_place_accessibility")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
