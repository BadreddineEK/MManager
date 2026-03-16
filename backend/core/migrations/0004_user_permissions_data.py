"""
Migration 0004 — Ajout du champ permissions_data + rôle VIEWER sur User
"""
from django.db import migrations, models


def _default_permissions():
    return {
        "school":      {"read": False, "write": False, "delete": False},
        "membership":  {"read": False, "write": False, "delete": False},
        "treasury":    {"read": False, "write": False, "delete": False},
        "campaigns":   {"read": False, "write": False, "delete": False},
        "users":       {"read": False, "write": False, "delete": False},
        "settings":    {"read": False, "write": False},
    }


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_mosquesettings_kpi_widgets"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="permissions_data",
            field=models.JSONField(
                default=_default_permissions,
                verbose_name="Permissions granulaires",
                help_text="JSON : {school:{read,write,delete}, membership:…}",
            ),
        ),
    ]
