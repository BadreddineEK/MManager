"""
Modèles core — Étape 2 : modèles complets.

- Mosque          : entité racine multi-tenant
- MosqueSettings  : configuration paramétrable par mosquée
- User            : utilisateur étendu (mosque + role)
- AuditLog        : journal d'audit des actions sensibles
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Mosque(TenantMixin):
    """Entité racine multi-tenant — une ligne par mosquée (hérite TenantMixin).
    
    TenantMixin ajoute automatiquement : schema_name (SlugField unique, requis)
    Le champ slug est conservé pour la compatibilité avec les URLs existantes.
    auto_create_schema = True : le schéma PostgreSQL est créé automatiquement au save().
    """

    auto_create_schema = True

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

    def __str__(self) -> str:
        return self.name


class Domain(DomainMixin):
    """Domaine associé à un tenant (sous-domaine nidham.fr ou nidham.local).
    
    DomainMixin ajoute : domain (CharField), tenant (FK→Mosque), is_primary (bool).
    """
    pass


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

    # ── Notifications email ─────────────────────────────────────────────────
    smtp_host = models.CharField(
        max_length=200, blank=True, default="",
        verbose_name="SMTP : hôte",
        help_text="Ex: smtp.gmail.com, ssl0.ovh.net",
    )
    smtp_port = models.PositiveSmallIntegerField(
        default=587,
        verbose_name="SMTP : port",
        help_text="587 (TLS/STARTTLS) ou 465 (SSL)",
    )
    smtp_user = models.CharField(
        max_length=200, blank=True, default="",
        verbose_name="SMTP : utilisateur",
    )
    smtp_password = models.CharField(
        max_length=200, blank=True, default="",
        verbose_name="SMTP : mot de passe",
    )
    smtp_use_tls = models.BooleanField(
        default=True,
        verbose_name="SMTP : utiliser TLS (STARTTLS)",
    )
    email_from = models.EmailField(
        blank=True, default="",
        verbose_name="Expéditeur des emails",
        help_text="Ex: noreply@mosquee-meximieux.fr",
    )
    email_subject_prefix = models.CharField(
        max_length=100, blank=True, default="[Mosquée Manager]",
        verbose_name="Préfixe sujet email",
    )

    class Meta:
        verbose_name = "Paramètres mosquée"
        verbose_name_plural = "Paramètres mosquées"
        db_table = "core_mosquesettings"

    def __str__(self) -> str:
        return f"Paramètres — {self.mosque.name}"


def _default_permissions():
    """Permissions par défaut : aucune (doit être explicitement accordé)."""
    return {
        "school":      {"read": False, "write": False, "delete": False},
        "membership":  {"read": False, "write": False, "delete": False},
        "treasury":    {"read": False, "write": False, "delete": False},
        "campaigns":   {"read": False, "write": False, "delete": False},
        "users":       {"read": False, "write": False, "delete": False},
        "settings":    {"read": False, "write": False},
    }


def _admin_permissions():
    """Permissions complètes pour un ADMIN."""
    return {
        "school":      {"read": True, "write": True, "delete": True},
        "membership":  {"read": True, "write": True, "delete": True},
        "treasury":    {"read": True, "write": True, "delete": True},
        "campaigns":   {"read": True, "write": True, "delete": True},
        "users":       {"read": True, "write": True, "delete": True},
        "settings":    {"read": True, "write": True},
    }


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
        ("VIEWER", "Lecture seule"),
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
    permissions_data = models.JSONField(
        default=_default_permissions,
        verbose_name="Permissions granulaires",
        help_text="JSON : {school:{read,write,delete}, membership:…, treasury:…, campaigns:…, users:…, settings:…}",
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

    @property
    def is_viewer(self) -> bool:
        return self.role == "VIEWER"

    def get_effective_permissions(self) -> dict:
        """
        Retourne les permissions effectives.
        - Superuser / ADMIN → permissions complètes
        - Autres rôles → permissions_data (granulaires)
        """
        if self.is_superuser or self.role == "ADMIN":
            return _admin_permissions()
        return self.permissions_data or _default_permissions()

    def can(self, module: str, action: str) -> bool:
        """
        Vérifie si l'utilisateur a le droit `action` sur `module`.
        Ex: user.can('treasury', 'write')
        """
        if self.is_superuser or self.role == "ADMIN":
            return True
        perms = self.get_effective_permissions()
        return bool(perms.get(module, {}).get(action, False))


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


class BankAccount(models.Model):
    """
    Compte bancaire d'une mosquée.

    Chaque mosquée peut avoir plusieurs comptes (1901, 1905, etc.).
    Le numéro de compte sert de clé d'identification lors de l'import CSV.
    """

    REGIME_CHOICES = [
        ("1901", "Loi 1901 — Association"),
        ("1905", "Loi 1905 — Culte"),
        ("autre", "Autre"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
        verbose_name="Mosquée",
    )
    label = models.CharField(
        max_length=100,
        verbose_name="Libellé",
        help_text='Ex : "Compte 1901 — Banque Populaire"',
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Nom de la banque",
    )
    account_number = models.CharField(
        max_length=50,
        verbose_name="Numéro de compte",
        help_text="Numéro tel qu'il apparaît dans les exports CSV de la banque",
    )
    regime = models.CharField(
        max_length=10,
        choices=REGIME_CHOICES,
        default="1901",
        verbose_name="Régime fiscal",
    )
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compte bancaire"
        verbose_name_plural = "Comptes bancaires"
        db_table = "core_bankaccount"
        ordering = ["regime", "label"]

    def __str__(self) -> str:
        return f"{self.label} ({self.account_number})"


class DispatchRule(models.Model):
    """
    Règle de dispatch automatique lors de l'import CSV bancaire.

    Si le Libellé ou le Détail d'une ligne CSV contient `keyword`,
    la transaction est automatiquement catégorisée avec `category` et `direction`.
    Les règles sont évaluées dans l'ordre `priority` (plus petit = plus prioritaire).
    """

    FIELD_CHOICES = [
        ("label", "Libellé"),
        ("detail", "Détail"),
        ("both", "Libellé ou Détail"),
    ]

    DIRECTION_CHOICES = [
        ("IN", "Entrée"),
        ("OUT", "Sortie"),
        ("auto", "Automatique (selon Débit/Crédit)"),
    ]

    CATEGORY_CHOICES = [
        ("don", "Don / Sadaqa"),
        ("loyer", "Loyer"),
        ("salaire", "Salaire / Honoraires"),
        ("facture", "Facture / Charges"),
        ("ecole", "Ecole coranique"),
        ("cotisation", "Cotisation adhérent"),
        ("projet", "Projet / Travaux"),
        ("subvention", "Subvention"),
        ("autre", "Autre"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="dispatch_rules",
        verbose_name="Mosquée",
    )
    keyword = models.CharField(
        max_length=200,
        verbose_name="Mot-clé",
        help_text="Texte à rechercher (insensible à la casse)",
    )
    field = models.CharField(
        max_length=10,
        choices=FIELD_CHOICES,
        default="both",
        verbose_name="Champ à inspecter",
    )
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        verbose_name="Catégorie à affecter",
    )
    direction = models.CharField(
        max_length=5,
        choices=DIRECTION_CHOICES,
        default="auto",
        verbose_name="Direction",
        help_text="'auto' utilise Débit/Crédit du CSV pour déterminer IN ou OUT",
    )
    priority = models.PositiveSmallIntegerField(
        default=10,
        verbose_name="Priorité",
        help_text="Plus petit = évalué en premier. En cas d'égalité, ordre alphabétique.",
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Règle de dispatch"
        verbose_name_plural = "Règles de dispatch"
        db_table = "core_dispatchrule"
        ordering = ["priority", "keyword"]

    def __str__(self) -> str:
        return f'"{self.keyword}" → {self.category} ({self.get_direction_display()})'


class Staff(models.Model):
    """
    Personnel de l'association — toute personne rémunérée.

    Exemples : Enseignant, Imam, Agent d'entretien, Comptable, Gardien...
    Le champ `name_keyword` sert à faire correspondre automatiquement les
    virements bancaires importés (matching insensible à la casse dans le libellé).
    """

    ROLE_CHOICES = [
        ("enseignant", "Enseignant(e)"),
        ("imam",       "Imam / Prédicateur"),
        ("entretien",  "Agent d'entretien"),
        ("comptable",  "Comptable / Trésorier"),
        ("gardien",    "Gardien / Accueil"),
        ("autre",      "Autre"),
    ]

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="staff_members",
        verbose_name="Mosquée",
    )
    full_name = models.CharField(
        max_length=200,
        verbose_name="Nom complet",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="enseignant",
        verbose_name="Rôle",
    )
    monthly_salary = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Salaire mensuel (€)",
        help_text="Montant brut mensuel à titre indicatif",
    )
    iban_fragment = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Fragment IBAN / nom banque",
        help_text="Ex: 'ZABI' ou 'SAMAALI' — utilisé pour reconnaître les virements dans le CSV",
    )
    name_keyword = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Mot-clé de reconnaissance",
        help_text="Texte recherché dans le libellé du virement (insensible à la casse). Ex: 'SABYA ZABI'",
    )
    phone = models.CharField(max_length=20, blank=True, default="", verbose_name="Téléphone")
    email = models.EmailField(blank=True, default="", verbose_name="Email")
    note = models.TextField(blank=True, default="", verbose_name="Note")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    start_date = models.DateField(null=True, blank=True, verbose_name="Date d'embauche")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin de contrat")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_staff"
        ordering = ["role", "full_name"]
        verbose_name = "Membre du personnel"
        verbose_name_plural = "Personnel"

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_role_display()}) — {self.mosque.name}"
