"""
Modèles core — Étape 2 : modèles complets.

- Mosque          : entité racine multi-tenant
- MosqueSettings  : configuration paramétrable par mosquée
- User            : utilisateur étendu (mosque + role)
- AuditLog        : journal d'audit des actions sensibles
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class Mosque(models.Model):
    """Entité racine multi-tenant — une ligne par mosquée."""

    name = models.CharField(max_length=200, verbose_name="Nom")
    slug = models.SlugField(unique=True, verbose_name="Identifiant URL")
    timezone = models.CharField(
        max_length=50,
        default="Europe/Paris",
        verbose_name="Fuseau horaire",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mosquée"
        verbose_name_plural = "Mosquées"
        db_table = "core_mosque"

    def __str__(self) -> str:
        return self.name


class MosqueSettings(models.Model):
    """
    Configuration paramétrable d'une mosquée.

    Remplace les valeurs figées en base : tarifs, niveaux, règles.
    Accessible uniquement via le rôle ADMIN.
    """

    SCHOOL_FEE_MODE_CHOICES = [
        ("annual", "Annuel"),
        ("monthly", "Mensuel"),
    ]
    MEMBERSHIP_FEE_MODE_CHOICES = [
        ("per_person", "Par personne"),
        ("per_family", "Par famille"),
    ]

    mosque = models.OneToOneField(
        Mosque,
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name="Mosquée",
    )
    # École
    school_levels = models.JSONField(
        default=list,
        verbose_name="Niveaux école",
        help_text='Ex : ["NP","N1","N2","N3","N4","N5","N6"]',
    )
    school_fee_default = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Tarif école par défaut",
    )
    school_fee_mode = models.CharField(
        max_length=20,
        choices=SCHOOL_FEE_MODE_CHOICES,
        default="annual",
        verbose_name="Mode tarif école",
    )
    # Cotisations
    membership_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant cotisation",
    )
    membership_fee_mode = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_FEE_MODE_CHOICES,
        default="per_person",
        verbose_name="Mode cotisation",
    )
    # Année scolaire active
    active_school_year_label = models.CharField(
        max_length=50,
        verbose_name="Année scolaire active",
        help_text='Ex : "2025-2026"',
    )
    # Reçus fiscaux
    receipt_logo_url = models.URLField(
        blank=True, default="",
        verbose_name="URL du logo (reçus PDF)",
        help_text="URL publique vers le logo de la mosquée (PNG/JPG recommandé)",
    )
    receipt_address = models.TextField(
        blank=True, default="",
        verbose_name="Adresse (reçus PDF)",
        help_text="Adresse complète de la mosquée affichée sur les reçus",
    )
    receipt_phone = models.CharField(
        max_length=30, blank=True, default="",
        verbose_name="Téléphone (reçus PDF)",
    )
    receipt_legal_mention = models.TextField(
        blank=True, default="",
        verbose_name="Mention légale (reçus PDF)",
        help_text='Ex : "Association loi 1901 — Reçu de don déductible à 66% dans la limite de 20% du revenu imposable"',
    )
    # KPI — widgets visibles
    show_kpi_school     = models.BooleanField(default=True, verbose_name="KPI : afficher École")
    show_kpi_membership = models.BooleanField(default=True, verbose_name="KPI : afficher Adhérents")
    show_kpi_treasury   = models.BooleanField(default=True, verbose_name="KPI : afficher Trésorerie")
    show_kpi_campaigns  = models.BooleanField(default=True, verbose_name="KPI : afficher Cagnottes")
    kpi_refresh_secs    = models.PositiveIntegerField(
        default=60,
        verbose_name="KPI : fréquence de rafraîchissement (secondes)",
        help_text="Valeurs conseillées : 30, 60, 120, 300",
    )

    class Meta:
        verbose_name = "Paramètres mosquée"
        verbose_name_plural = "Paramètres mosquées"
        db_table = "core_mosquesettings"

    def __str__(self) -> str:
        return f"Paramètres — {self.mosque.name}"


class User(AbstractUser):
    """
    Utilisateur Mosquée Manager.

    Hérite de AbstractUser (username, email, password, is_staff, etc.).
    Chaque utilisateur est rattaché à une mosquée et possède un rôle RBAC.
    """

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("TRESORIER", "Trésorier"),
        ("ECOLE_MANAGER", "École Manager"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="Mosquée",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        blank=True,
        default="",
        verbose_name="Rôle",
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        db_table = "core_user"

    def __str__(self) -> str:
        return self.email or self.username

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN" or self.is_superuser

    @property
    def is_tresorier(self) -> bool:
        return self.role == "TRESORIER"

    @property
    def is_ecole_manager(self) -> bool:
        return self.role == "ECOLE_MANAGER"


class AuditLog(models.Model):
    """
    Journal d'audit immuable.

    Trace les actions sensibles : création/modif paiements, imports, exports.
    Ne jamais modifier ni supprimer une ligne d'audit.
    """

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        verbose_name="Mosquée",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
        verbose_name="Utilisateur",
    )
    action = models.CharField(max_length=50, verbose_name="Action")
    entity = models.CharField(max_length=50, verbose_name="Entité")
    entity_id = models.IntegerField(null=True, blank=True, verbose_name="ID entité")
    payload = models.JSONField(default=dict, verbose_name="Données")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log d'audit"
        verbose_name_plural = "Logs d'audit"
        db_table = "core_auditlog"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.action} {self.entity}#{self.entity_id}"
