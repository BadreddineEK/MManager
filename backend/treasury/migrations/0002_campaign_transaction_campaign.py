"""
Migration 0002 — Ajout du modèle Campaign + FK campaign sur TreasuryTransaction
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("treasury", "0001_initial"),
    ]

    operations = [
        # ── Créer la table Campaign ──────────────────────────────────────────
        migrations.CreateModel(
            name="Campaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="Nom de la cagnotte")),
                ("description", models.TextField(blank=True, default="", verbose_name="Description")),
                ("icon", models.CharField(default="🎯", max_length=10, verbose_name="Icône (emoji)")),
                ("goal_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name="Objectif (€)")),
                ("start_date", models.DateField(blank=True, null=True, verbose_name="Date de début")),
                ("end_date", models.DateField(blank=True, null=True, verbose_name="Date de fin")),
                ("status", models.CharField(
                    choices=[("active", "Active"), ("closed", "Clôturée")],
                    default="active", max_length=10, verbose_name="Statut",
                )),
                ("show_on_kpi", models.BooleanField(default=True, verbose_name="Afficher sur la page KPI publique")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("mosque", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="campaigns",
                    to="core.mosque",
                )),
            ],
            options={"db_table": "treasury_campaign", "ordering": ["-created_at"],
                     "verbose_name": "Cagnotte", "verbose_name_plural": "Cagnottes"},
        ),
        # ── Ajouter FK campaign sur TreasuryTransaction ──────────────────────
        migrations.AddField(
            model_name="treasurytransaction",
            name="campaign",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="treasury.campaign",
                verbose_name="Cagnotte liée",
            ),
        ),
    ]
