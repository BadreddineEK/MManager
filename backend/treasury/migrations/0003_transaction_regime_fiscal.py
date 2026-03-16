"""
Migration 0003 — Ajout du champ regime_fiscal sur TreasuryTransaction
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("treasury", "0002_campaign_transaction_campaign"),
    ]

    operations = [
        migrations.AddField(
            model_name="treasurytransaction",
            name="regime_fiscal",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Non précisé"),
                    ("1901", "Loi 1901 — Association"),
                    ("1905", "Loi 1905 — Culte"),
                ],
                default="",
                max_length=4,
                verbose_name="Régime fiscal",
            ),
        ),
    ]
