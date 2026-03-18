"""
Modeles membership -- Cotisations mosquee
==========================================
- MembershipYear    : annee de cotisation (ex: 2026)
- Member            : adherent (nom, tel, email)
- MembershipPayment : paiement de cotisation
"""
from django.db import models

from core.models import Mosque


class MembershipYear(models.Model):
    """Annee de cotisation d'une mosquee."""

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="membership_years",
        verbose_name="Mosquee",
    )
    year = models.IntegerField(verbose_name="Annee", help_text="Ex: 2026")
    amount_expected = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Montant attendu par adherent",
    )
    is_active = models.BooleanField(default=False, verbose_name="Annee active")

    class Meta:
        verbose_name = "Annee de cotisation"
        verbose_name_plural = "Annees de cotisation"
        db_table = "membership_year"
        unique_together = [("mosque", "year")]
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"{self.year} ({self.mosque.name})"


class Member(models.Model):
    """Adherent de la mosquee."""

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="Mosquee",
    )
    full_name = models.CharField(max_length=200, verbose_name="Nom complet")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    phone = models.CharField(max_length=50, blank=True, default="", verbose_name="Telephone")
    address = models.TextField(blank=True, default="", verbose_name="Adresse")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adherent"
        verbose_name_plural = "Adherents"
        db_table = "membership_member"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.mosque.name})"


class MembershipPayment(models.Model):
    """Paiement de cotisation d'un adherent."""

    METHOD_CHOICES = [
        ("cash", "Especes"),
        ("cheque", "Cheque"),
        ("virement", "Virement"),
        ("autre", "Autre"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="membership_payments",
        verbose_name="Mosquee",
    )
    membership_year = models.ForeignKey(
        MembershipYear,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Annee de cotisation",
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Adherent",
    )
    date = models.DateField(verbose_name="Date du paiement")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash", verbose_name="Mode")
    note = models.TextField(blank=True, default="", verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement cotisation"
        verbose_name_plural = "Paiements cotisations"
        db_table = "membership_payment"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.member.full_name} -- {self.amount}EUR ({self.date})"
