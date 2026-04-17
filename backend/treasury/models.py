"""
Modeles Tresorerie -- transactions financieres de la mosquee
=============================================================
TreasuryTransaction : toute entree ou sortie d'argent
  - direction : IN (entree) ou OUT (sortie)
  - category  : don, loyer, salaire, facture, ecole, cotisation, autre, ...
  - family    : FK optionnelle vers Family (paiement école)
  - school_year : FK optionnelle vers SchoolYear
  - member    : FK optionnelle vers Member (cotisation adhérent)
  - membership_year : FK optionnelle vers MembershipYear
"""
from django.db import models

from core.models import BankAccount, Mosque


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

    REGIME_CHOICES = [
        ("",     "Non précisé"),
        ("1901", "Loi 1901 — Association"),
        ("1905", "Loi 1905 — Culte"),
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
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="autre", blank=True)
    label = models.CharField(max_length=255)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    note = models.TextField(blank=True, default="")
    regime_fiscal = models.CharField(
        max_length=4,
        choices=REGIME_CHOICES,
        blank=True,
        default="",
        verbose_name="Régime fiscal",
    )
    campaign = models.ForeignKey(
        "Campaign",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Cagnotte liée",
    )
    # ── Liens optionnels vers les ressources humaines ──────────────────────
    # Remplis automatiquement lors de la saisie d'un paiement école ou cotisation
    family = models.ForeignKey(
        "school.Family",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Famille (école)",
    )
    school_year = models.ForeignKey(
        "school.SchoolYear",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Année scolaire",
    )
    member = models.ForeignKey(
        "membership.Member",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Adhérent",
    )
    membership_year = models.ForeignKey(
        "membership.MembershipYear",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Année de cotisation",
    )
    # ── Compte bancaire & import CSV ───────────────────────────────────────
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="transactions",
        verbose_name="Compte bancaire",
        help_text="Null = espèces / non bancaire",
    )
    source = models.CharField(
        max_length=15,
        choices=[
            ("manual",      "Saisie manuelle"),
            ("import",      "Import CSV bancaire"),
            ("cash_school", "Especes ecole"),
            ("cash_cotis",  "Especes cotisation"),
        ],
        default="manual",
        verbose_name="Source",
    )
    import_operation_id = models.CharField(
        max_length=250,
        null=True, blank=True,
        db_index=True,
        verbose_name="N° opération (import)",
        help_text="Identifiant unique de la ligne dans le CSV bancaire — sert à éviter les doublons",
    )
    import_status = models.CharField(
        max_length=15,
        choices=[
            ("validated", "Validée"),
            ("pending", "En attente de validation"),
        ],
        null=True, blank=True,
        verbose_name="Statut import",
        help_text="Null pour les transactions saisies manuellement",
    )
    # Liens vers paiements ecole / cotisation
    school_payment = models.OneToOneField(
        "school.SchoolPayment",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="treasury_tx",
        verbose_name="Paiement ecole lie",
    )
    membership_payment = models.OneToOneField(
        "membership.MembershipPayment",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="treasury_tx",
        verbose_name="Paiement cotisation lie",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "treasury_transaction"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date} — {self.label} ({self.amount} €)"


class CashCount(models.Model):
    """
    Pointage de caisse — snapshot des espèces disponibles à un instant T.

    Exemple : le trésorier compte les billets/pièces après la prière du vendredi
    et enregistre un pointage. Le total est calculé automatiquement depuis les lignes.
    """

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="cash_counts",
        verbose_name="Mosquée",
    )
    date = models.DateField(verbose_name="Date du pointage")
    note = models.TextField(blank=True, default="", verbose_name="Note / Commentaire")
    created_by = models.CharField(
        max_length=150, blank=True, default="", verbose_name="Saisi par"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "treasury_cashcount"
        ordering = ["-date", "-created_at"]
        verbose_name = "Pointage de caisse"
        verbose_name_plural = "Pointages de caisse"

    def __str__(self) -> str:
        return f"Caisse {self.date} — {self.mosque.name}"

    @property
    def total(self):
        """Somme de toutes les coupures × quantités."""
        result = self.lines.aggregate(
            total=models.Sum(models.F("denomination") * models.F("quantity"))
        )["total"]
        return result or 0


class CashDenomination(models.Model):
    """
    Ligne d'un pointage de caisse : une coupure et sa quantité.

    Exemple : denomination=50, quantity=12 → 12 billets de 50 € = 600 €
    """

    cash_count = models.ForeignKey(
        CashCount,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name="Pointage",
    )
    denomination = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name="Coupure (€)",
    )
    quantity = models.PositiveIntegerField(verbose_name="Quantité")

    class Meta:
        db_table = "treasury_cashdenomination"
        ordering = ["-denomination"]
        verbose_name = "Ligne de coupure"
        verbose_name_plural = "Lignes de coupures"
        unique_together = [("cash_count", "denomination")]

    def __str__(self) -> str:
        return f"{self.quantity} × {self.denomination} €"

    @property
    def subtotal(self):
        return float(self.denomination) * self.quantity


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
