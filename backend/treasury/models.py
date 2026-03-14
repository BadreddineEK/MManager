"""
Modeles Tresorerie -- transactions financieres de la mosquee
=============================================================
TreasuryTransaction : toute entree ou sortie d'argent
  - direction : IN (entree) ou OUT (sortie)
  - category  : don, loyer, salaire, facture, ecole, cotisation, autre, ...
"""
from django.db import models

from core.models import Mosque


class TreasuryTransaction(models.Model):

    DIRECTION_IN = "IN"
    DIRECTION_OUT = "OUT"
    DIRECTION_CHOICES = [
        (DIRECTION_IN, "Entree"),
        (DIRECTION_OUT, "Sortie"),
    ]

    METHOD_CHOICES = [
        ("cash", "Especes"),
        ("cheque", "Cheque"),
        ("virement", "Virement"),
        ("autre", "Autre"),
    ]

    CATEGORY_CHOICES = [
        ("don", "Don / Sadaqa"),
        ("loyer", "Loyer"),
        ("salaire", "Salaire / Honoraires"),
        ("facture", "Facture / Charges"),
        ("ecole", "Ecole coranique"),
        ("cotisation", "Cotisation adherent"),
        ("projet", "Projet / Travaux"),
        ("subvention", "Subvention"),
        ("autre", "Autre"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    date = models.DateField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="autre")
    label = models.CharField(max_length=255)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "treasury_transaction"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"[{self.direction}] {self.label} — {self.amount} € ({self.date})"
