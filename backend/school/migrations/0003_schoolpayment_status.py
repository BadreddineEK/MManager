"""
Migration 0003 : ajout status sur SchoolPayment
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("school", "0002_school_v2_classes_attendance_quran"),
    ]

    operations = [
        migrations.AddField(
            model_name="schoolpayment",
            name="status",
            field=models.CharField(
                max_length=15,
                choices=[("validated", "Valide"), ("pending", "En attente")],
                default="validated",
                verbose_name="Statut",
            ),
        ),
    ]
