"""
Migration 0002 : liens directs SchoolPayment / MembershipPayment <-> TreasuryTransaction
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("treasury", "0001_initial"),
        ("school", "0002_school_v2_classes_attendance_quran"),
        ("membership", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="treasurytransaction",
            name="source",
            field=models.CharField(
                max_length=15,
                choices=[
                    ("manual",      "Saisie manuelle"),
                    ("import",      "Import CSV bancaire"),
                    ("cash_school", "Especes ecole"),
                    ("cash_cotis",  "Especes cotisation"),
                ],
                default="manual",
                verbose_name="Source",
            ),
        ),
        migrations.AddField(
            model_name="treasurytransaction",
            name="school_payment",
            field=models.OneToOneField(
                to="school.SchoolPayment",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True, blank=True,
                related_name="treasury_tx",
                verbose_name="Paiement ecole lie",
            ),
        ),
        migrations.AddField(
            model_name="treasurytransaction",
            name="membership_payment",
            field=models.OneToOneField(
                to="membership.MembershipPayment",
                on_delete=django.db.models.deletion.SET_NULL,
                null=True, blank=True,
                related_name="treasury_tx",
                verbose_name="Paiement cotisation lie",
            ),
        ),
    ]
