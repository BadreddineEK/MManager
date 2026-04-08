# Generated manually 2026-04-08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_add_smtp_settings_to_mosquesettings"),
    ]

    operations = [
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=100, verbose_name="Libelle")),
                ("bank_name", models.CharField(blank=True, default="", max_length=100, verbose_name="Nom de la banque")),
                ("account_number", models.CharField(max_length=50, verbose_name="Numero de compte")),
                ("regime", models.CharField(choices=[("1901", "Loi 1901 — Association"), ("1905", "Loi 1905 — Culte"), ("autre", "Autre")], default="1901", max_length=10, verbose_name="Regime fiscal")),
                ("is_active", models.BooleanField(default=True, verbose_name="Actif")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_accounts", to="core.mosque", verbose_name="Mosquee")),
            ],
            options={
                "verbose_name": "Compte bancaire",
                "verbose_name_plural": "Comptes bancaires",
                "db_table": "core_bankaccount",
                "ordering": ["regime", "label"],
            },
        ),
        migrations.CreateModel(
            name="DispatchRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("keyword", models.CharField(max_length=200, verbose_name="Mot-cle")),
                ("field", models.CharField(choices=[("label", "Libelle"), ("detail", "Detail"), ("both", "Libelle ou Detail")], default="both", max_length=10, verbose_name="Champ")),
                ("category", models.CharField(choices=[("don", "Don"), ("loyer", "Loyer"), ("salaire", "Salaire"), ("facture", "Facture"), ("ecole", "Ecole"), ("cotisation", "Cotisation"), ("projet", "Projet"), ("subvention", "Subvention"), ("autre", "Autre")], max_length=30, verbose_name="Categorie")),
                ("direction", models.CharField(choices=[("IN", "Entree"), ("OUT", "Sortie"), ("auto", "Automatique")], default="auto", max_length=5, verbose_name="Direction")),
                ("priority", models.PositiveSmallIntegerField(default=10, verbose_name="Priorite")),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("mosque", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="dispatch_rules", to="core.mosque", verbose_name="Mosquee")),
            ],
            options={
                "verbose_name": "Regle de dispatch",
                "verbose_name_plural": "Regles de dispatch",
                "db_table": "core_dispatchrule",
                "ordering": ["priority", "keyword"],
            },
        ),
    ]
