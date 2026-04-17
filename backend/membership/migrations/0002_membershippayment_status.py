"""
Migration 0002 : ajout status sur MembershipPayment
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("membership", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershippayment",
            name="status",
            field=models.CharField(
                max_length=15,
                choices=[("validated", "Valide"), ("pending", "En attente")],
                default="validated",
                verbose_name="Statut",
            ),
        ),
    ]
