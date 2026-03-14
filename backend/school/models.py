"""
Modeles school -- Ecole coranique
===================================
- SchoolYear    : annee scolaire (ex: 2025-2026)
- Family        : famille (parent, telephone, email)
- Child         : enfant rattache a une famille
- SchoolPayment : paiement d'une famille pour l'ecole
"""
from django.db import models

from core.models import Mosque


class SchoolYear(models.Model):
    """Annee scolaire d'une mosquee."""

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="school_years",
        verbose_name="Mosquee",
    )
    label = models.CharField(max_length=50, verbose_name="Label", help_text='Ex: "2025-2026"')
    start_date = models.DateField(verbose_name="Date de debut")
    end_date = models.DateField(verbose_name="Date de fin")
    is_active = models.BooleanField(default=False, verbose_name="Annee active")

    class Meta:
        verbose_name = "Annee scolaire"
        verbose_name_plural = "Annees scolaires"
        db_table = "school_year"
        unique_together = [("mosque", "label")]
        ordering = ["-start_date"]

    def __str__(self) -> str:
        return f"{self.label} ({self.mosque.name})"


class Family(models.Model):
    """Famille inscrite a l'ecole coranique."""

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="families",
        verbose_name="Mosquee",
    )
    primary_contact_name = models.CharField(max_length=200, verbose_name="Nom du contact principal")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    phone1 = models.CharField(max_length=20, verbose_name="Telephone principal")
    phone2 = models.CharField(max_length=20, blank=True, default="", verbose_name="Telephone secondaire")
    address = models.TextField(blank=True, default="", verbose_name="Adresse")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Famille"
        verbose_name_plural = "Familles"
        db_table = "school_family"
        ordering = ["primary_contact_name"]

    def __str__(self) -> str:
        return f"{self.primary_contact_name} ({self.mosque.name})"


class Child(models.Model):
    """Enfant inscrit a l'ecole coranique."""

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="Mosquee",
    )
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="Famille",
    )
    first_name = models.CharField(max_length=100, verbose_name="Prenom")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    level = models.CharField(max_length=20, verbose_name="Niveau", help_text="Ex: NP, N1, N2...")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Enfant"
        verbose_name_plural = "Enfants"
        db_table = "school_child"
        ordering = ["family__primary_contact_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} ({self.family.primary_contact_name})"


class SchoolPayment(models.Model):
    """Paiement ecole d'une famille pour une annee scolaire."""

    METHOD_CHOICES = [
        ("cash", "Especes"),
        ("cheque", "Cheque"),
        ("virement", "Virement"),
        ("autre", "Autre"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="school_payments",
        verbose_name="Mosquee",
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Annee scolaire",
    )
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Famille",
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        verbose_name="Enfant (optionnel)",
    )
    date = models.DateField(verbose_name="Date du paiement")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash", verbose_name="Mode de paiement")
    note = models.TextField(blank=True, default="", verbose_name="Note")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement ecole"
        verbose_name_plural = "Paiements ecole"
        db_table = "school_payment"
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.family.primary_contact_name} -- {self.amount}EUR ({self.date})"
