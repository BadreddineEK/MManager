"""
Migration 0003 — Ajout des champs KPI widgets sur MosqueSettings
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_mosquesettings_receipt_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="mosquesettings",
            name="show_kpi_school",
            field=models.BooleanField(default=True, verbose_name="KPI : afficher École"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="show_kpi_membership",
            field=models.BooleanField(default=True, verbose_name="KPI : afficher Adhérents"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="show_kpi_treasury",
            field=models.BooleanField(default=True, verbose_name="KPI : afficher Trésorerie"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="show_kpi_campaigns",
            field=models.BooleanField(default=True, verbose_name="KPI : afficher Cagnottes"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="kpi_refresh_secs",
            field=models.PositiveIntegerField(
                default=60,
                verbose_name="KPI : fréquence de rafraîchissement (secondes)",
            ),
        ),
    ]
