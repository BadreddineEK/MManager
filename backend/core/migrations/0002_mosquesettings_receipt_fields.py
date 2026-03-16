"""
Migration 0002 — Ajout des champs reçus fiscaux sur MosqueSettings
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mosquesettings",
            name="receipt_logo_url",
            field=models.URLField(blank=True, default="", verbose_name="URL du logo (reçus PDF)"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="receipt_address",
            field=models.TextField(blank=True, default="", verbose_name="Adresse (reçus PDF)"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="receipt_phone",
            field=models.CharField(blank=True, default="", max_length=30, verbose_name="Téléphone (reçus PDF)"),
        ),
        migrations.AddField(
            model_name="mosquesettings",
            name="receipt_legal_mention",
            field=models.TextField(blank=True, default="", verbose_name="Mention légale (reçus PDF)"),
        ),
    ]
