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
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Cagnotte liée",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "treasury_transaction"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} — {self.label} ({self.amount} €)"


class Campaign(models.Model):
    """
    Cagnotte / Collecte liée à un objectif financier.

    Exemples : Cagnotte Ramadan, Réparation toiture, Achat tapis...
    Les transactions trésorerie peuvent être rattachées à une cagnotte.
    """

    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Clôturée"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="campaigns",
    )
    name = models.CharField(max_length=200, verbose_name="Nom de la cagnotte")
    description = models.TextField(blank=True, default="", verbose_name="Description")
    icon = models.CharField(max_length=10, default="🎯", verbose_name="Icône (emoji)")
    goal_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Objectif (€)"
    )
    start_date = models.DateField(null=True, blank=True, verbose_name="Date de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE,
        verbose_name="Statut"
    )
    show_on_kpi = models.BooleanField(
        default=True, verbose_name="Afficher sur la page KPI publique"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "treasury_campaign"
        ordering = ["-created_at"]
        verbose_name = "Cagnotte"
        verbose_name_plural = "Cagnottes"

    def __str__(self) -> str:
        return f"{self.name} ({self.mosque.name})"

    @property
    def collected_amount(self) -> float:
        """Somme des transactions IN liées à cette cagnotte."""
        total = self.transactions.filter(direction="IN").aggregate(
            total=models.Sum("amount")
        )["total"]
        return float(total or 0)

    @property
    def progress_percent(self) -> int:
        """Pourcentage atteint (0-100, plafonné à 100)."""
        if not self.goal_amount or float(self.goal_amount) == 0:
            return 0
        pct = (self.collected_amount / float(self.goal_amount)) * 100
        return min(int(pct), 100)
        return f"[{self.direction}] {self.label} — {self.amount} € ({self.date})"
