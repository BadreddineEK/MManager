# Generated manually 2026-04-08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_add_bankaccount_dispatchrule"),
        ("treasury", "0004_add_family_member_fk_to_transaction"),
    ]

    operations = [
        migrations.AlterField(
            model_name="treasurytransaction",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("don", "Don / Sadaqa"),
                    ("loyer", "Loyer"),
                    ("salaire", "Salaire / Honoraires"),
                    ("facture", "Facture / Charges"),
                    ("ecole", "Ecole coranique"),
                    ("cotisation", "Cotisation adherent"),
                    ("projet", "Projet / Travaux"),
                    ("subvention", "Subvention"),
                    ("autre", "Autre"),
                ],
                default="autre",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="treasurytransaction",
            name="bank_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="core.bankaccount",
                verbose_name="Compte bancaire",
            ),
        ),
        migrations.AddField(
            model_name="treasurytransaction",
            name="source",
            field=models.CharField(
                choices=[("manual", "Saisie manuelle"), ("import", "Import CSV")],
                default="manual",
                max_length=10,
                verbose_name="Source",
            ),
        ),
        migrations.AddField(
            model_name="treasurytransaction",
            name="import_operation_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=250,
                null=True,
                verbose_name="N operation (import)",
            ),
        ),
        migrations.AddField(
            model_name="treasurytransaction",
            name="import_status",
            field=models.CharField(
                blank=True,
                choices=[("validated", "Validee"), ("pending", "En attente")],
                max_length=15,
                null=True,
                verbose_name="Statut import",
            ),
        ),
    ]
