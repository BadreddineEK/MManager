"""
Modeles school -- Ecole coranique v2
=====================================
Modeles existants (inchanges) :
  SchoolYear    : annee scolaire
  Family        : famille
  Child         : enfant
  SchoolPayment : paiement ecole

Nouveaux modeles (v2) :
  Class           : classe / niveau (ex: NP, N1, N2 Coran)
  ClassEnrollment : inscription d'un enfant dans une classe
  Attendance      : appel / presence par seance
  QuranProgress   : suivi memorisation Coran par enfant
  GradePeriod     : periode d'appreciation (ex: Trimestre 1)
  Grade           : appreciation d'un enfant pour une periode
"""
from django.conf import settings
from django.db import models

from core.models import Mosque


# ─────────────────────────────────────────────────────────────────────────────
# Modeles existants — inchanges
# ─────────────────────────────────────────────────────────────────────────────

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

    def __str__(self):
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
    phone1 = models.CharField(max_length=50, blank=True, default="", verbose_name="Telephone principal")
    phone2 = models.CharField(max_length=50, blank=True, default="", verbose_name="Telephone secondaire")
    address = models.TextField(blank=True, default="", verbose_name="Adresse")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Famille"
        verbose_name_plural = "Familles"
        db_table = "school_family"
        ordering = ["primary_contact_name"]

    def __str__(self):
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
    level = models.CharField(max_length=50, verbose_name="Niveau", help_text="Ex: NP, N1, N2...")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Enfant"
        verbose_name_plural = "Enfants"
        db_table = "school_child"
        ordering = ["family__primary_contact_name", "first_name"]

    def __str__(self):
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

    def __str__(self):
        return f"{self.family.primary_contact_name} -- {self.amount}EUR ({self.date})"


# ─────────────────────────────────────────────────────────────────────────────
# NOUVEAUX modeles v2
# ─────────────────────────────────────────────────────────────────────────────

class Class(models.Model):
    """
    Classe / groupe de l'ecole coranique.
    Ex: Petits (NP), Debutants (N1), Intermediaires (N2), Avances (N3), Coran.
    """

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="school_classes",
        verbose_name="Mosquee",
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name="classes",
        verbose_name="Annee scolaire",
    )
    name = models.CharField(max_length=100, verbose_name="Nom de la classe", help_text='Ex: "N1 - Debutants"')
    level_code = models.CharField(max_length=20, verbose_name="Code niveau", help_text='Ex: "NP", "N1", "N2", "CORAN"')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching_classes",
        verbose_name="Professeur principal",
    )
    room = models.CharField(max_length=100, blank=True, default="", verbose_name="Salle")
    schedule_notes = models.TextField(blank=True, default="", verbose_name="Horaires / notes")
    max_students = models.PositiveIntegerField(null=True, blank=True, verbose_name="Capacite max")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordre d'affichage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        db_table = "school_class"
        ordering = ["order", "name"]
        unique_together = [("mosque", "school_year", "level_code")]

    def __str__(self):
        return f"{self.name} ({self.school_year.label})"

    @property
    def student_count(self):
        return self.enrollments.filter(is_active=True).count()


class ClassEnrollment(models.Model):
    """
    Inscription d'un enfant dans une classe pour une annee scolaire.
    Un enfant peut changer de classe en cours d'annee (is_active=False sur l'ancien).
    """

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Mosquee",
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Classe",
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Enfant",
    )
    enrolled_at = models.DateField(auto_now_add=True, verbose_name="Date d'inscription")
    is_active = models.BooleanField(default=True, verbose_name="Inscription active")
    notes = models.TextField(blank=True, default="", verbose_name="Notes")

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        db_table = "school_enrollment"
        unique_together = [("school_class", "child")]
        ordering = ["child__first_name"]

    def __str__(self):
        return f"{self.child.first_name} -> {self.school_class.name}"


class AttendanceSession(models.Model):
    """
    Seance de cours (1 appel = 1 seance).
    Creee par le prof au moment de faire l'appel.
    """

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name="sessions",
        verbose_name="Classe",
    )
    date = models.DateField(verbose_name="Date de la seance")
    notes = models.TextField(blank=True, default="", verbose_name="Notes prof")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seance"
        verbose_name_plural = "Seances"
        db_table = "school_attendance_session"
        unique_together = [("school_class", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.school_class.name} — {self.date}"


class Attendance(models.Model):
    """
    Presence d'un enfant a une seance.
    1 ligne par enfant par seance.
    """

    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"
    STATUS_LATE = "late"
    STATUS_EXCUSED = "excused"

    STATUS_CHOICES = [
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
        (STATUS_LATE, "En retard"),
        (STATUS_EXCUSED, "Absent excuse"),
    ]

    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="attendances",
        verbose_name="Seance",
    )
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="attendances",
        verbose_name="Enfant",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PRESENT,
        verbose_name="Statut",
    )
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="Note")

    class Meta:
        verbose_name = "Presence"
        verbose_name_plural = "Presences"
        db_table = "school_attendance"
        unique_together = [("session", "child")]
        ordering = ["child__first_name"]

    def __str__(self):
        return f"{self.child.first_name} — {self.session.date} — {self.status}"


# ─────────────────────────────────────────────────────────────────────────────
# Suivi Coran
# ─────────────────────────────────────────────────────────────────────────────

SURAH_CHOICES = [
    (1,  "Al-Fatiha"), (2, "Al-Baqara"), (3, "Al-Imran"), (4, "An-Nisa"),
    (5, "Al-Maida"), (6, "Al-Anam"), (7, "Al-Araf"), (8, "Al-Anfal"),
    (9, "At-Tawba"), (10, "Yunus"), (11, "Hud"), (12, "Yusuf"),
    (13, "Ar-Rad"), (14, "Ibrahim"), (15, "Al-Hijr"), (16, "An-Nahl"),
    (17, "Al-Isra"), (18, "Al-Kahf"), (19, "Maryam"), (20, "Ta-Ha"),
    (21, "Al-Anbiya"), (22, "Al-Hajj"), (23, "Al-Muminun"), (24, "An-Nur"),
    (25, "Al-Furqan"), (26, "Ash-Shuara"), (27, "An-Naml"), (28, "Al-Qasas"),
    (29, "Al-Ankabut"), (30, "Ar-Rum"), (31, "Luqman"), (32, "As-Sajda"),
    (33, "Al-Ahzab"), (34, "Saba"), (35, "Fatir"), (36, "Ya-Sin"),
    (37, "As-Saffat"), (38, "Sad"), (39, "Az-Zumar"), (40, "Ghafir"),
    (41, "Fussilat"), (42, "Ash-Shura"), (43, "Az-Zukhruf"), (44, "Ad-Dukhan"),
    (45, "Al-Jathiya"), (46, "Al-Ahqaf"), (47, "Muhammad"), (48, "Al-Fath"),
    (49, "Al-Hujurat"), (50, "Qaf"), (51, "Adh-Dhariyat"), (52, "At-Tur"),
    (53, "An-Najm"), (54, "Al-Qamar"), (55, "Ar-Rahman"), (56, "Al-Waqia"),
    (57, "Al-Hadid"), (58, "Al-Mujadila"), (59, "Al-Hashr"), (60, "Al-Mumtahana"),
    (61, "As-Saf"), (62, "Al-Jumuah"), (63, "Al-Munafiqun"), (64, "At-Taghabun"),
    (65, "At-Talaq"), (66, "At-Tahrim"), (67, "Al-Mulk"), (68, "Al-Qalam"),
    (69, "Al-Haqqa"), (70, "Al-Maarij"), (71, "Nuh"), (72, "Al-Jinn"),
    (73, "Al-Muzzammil"), (74, "Al-Muddaththir"), (75, "Al-Qiyama"), (76, "Al-Insan"),
    (77, "Al-Mursalat"), (78, "An-Naba"), (79, "An-Naziat"), (80, "Abasa"),
    (81, "At-Takwir"), (82, "Al-Infitar"), (83, "Al-Mutaffifin"), (84, "Al-Inshiqaq"),
    (85, "Al-Buruj"), (86, "At-Tariq"), (87, "Al-Ala"), (88, "Al-Ghashiya"),
    (89, "Al-Fajr"), (90, "Al-Balad"), (91, "Ash-Shams"), (92, "Al-Layl"),
    (93, "Ad-Duha"), (94, "Ash-Sharh"), (95, "At-Tin"), (96, "Al-Alaq"),
    (97, "Al-Qadr"), (98, "Al-Bayyina"), (99, "Az-Zalzala"), (100, "Al-Adiyat"),
    (101, "Al-Qaria"), (102, "At-Takathur"), (103, "Al-Asr"), (104, "Al-Humaza"),
    (105, "Al-Fil"), (106, "Quraysh"), (107, "Al-Maun"), (108, "Al-Kawthar"),
    (109, "Al-Kafirun"), (110, "An-Nasr"), (111, "Al-Masad"), (112, "Al-Ikhlas"),
    (113, "Al-Falaq"), (114, "An-Nas"),
]


class QuranProgress(models.Model):
    """
    Suivi de memorisation d'une sourate par un enfant.
    1 ligne par sourate par enfant.
    """

    STATUS_NOT_STARTED = "not_started"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_MEMORIZED   = "memorized"
    STATUS_REVIEW      = "review"

    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, "Non commence"),
        (STATUS_IN_PROGRESS, "En cours"),
        (STATUS_MEMORIZED,   "Memorise"),
        (STATUS_REVIEW,      "En revision"),
    ]

    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="quran_progress",
        verbose_name="Enfant",
    )
    surah_number = models.PositiveSmallIntegerField(
        choices=SURAH_CHOICES,
        verbose_name="Sourate",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default=STATUS_NOT_STARTED,
        verbose_name="Statut",
    )
    started_at = models.DateField(null=True, blank=True, verbose_name="Debut")
    completed_at = models.DateField(null=True, blank=True, verbose_name="Memorisee le")
    notes = models.CharField(max_length=255, blank=True, default="", verbose_name="Notes prof")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quran_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Progression Coran"
        verbose_name_plural = "Progressions Coran"
        db_table = "school_quran_progress"
        unique_together = [("child", "surah_number")]
        ordering = ["child", "surah_number"]

    def __str__(self):
        return f"{self.child.first_name} — Sourate {self.surah_number} — {self.status}"


# ─────────────────────────────────────────────────────────────────────────────
# Bulletins / Appreciations
# ─────────────────────────────────────────────────────────────────────────────

class GradePeriod(models.Model):
    """
    Periode d'appreciation (trimestre, semestre...).
    Ex: Trimestre 1 2025-2026.
    """

    mosque = models.ForeignKey(
        Mosque,
        on_delete=models.CASCADE,
        related_name="grade_periods",
    )
    school_year = models.ForeignKey(
        SchoolYear,
        on_delete=models.CASCADE,
        related_name="grade_periods",
        verbose_name="Annee scolaire",
    )
    name = models.CharField(max_length=100, verbose_name="Nom", help_text='Ex: "Trimestre 1"')
    start_date = models.DateField(verbose_name="Debut")
    end_date = models.DateField(verbose_name="Fin")
    is_published = models.BooleanField(default=False, verbose_name="Bulletins publies")
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        verbose_name = "Periode"
        verbose_name_plural = "Periodes"
        db_table = "school_grade_period"
        unique_together = [("school_year", "name")]
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} — {self.school_year.label}"


class Grade(models.Model):
    """
    Appreciation d'un enfant pour une periode.
    Generee par le prof, consultee dans le bulletin PDF.
    """

    MENTION_CHOICES = [
        ("TB", "Tres bien"),
        ("B",  "Bien"),
        ("AB", "Assez bien"),
        ("P",  "Peut mieux faire"),
        ("I",  "Insuffisant"),
    ]

    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        related_name="grades",
        verbose_name="Enfant",
    )
    period = models.ForeignKey(
        GradePeriod,
        on_delete=models.CASCADE,
        related_name="grades",
        verbose_name="Periode",
    )
    school_class = models.ForeignKey(
        Class,
        on_delete=models.SET_NULL,
        null=True,
        related_name="grades",
        verbose_name="Classe",
    )
    mention = models.CharField(
        max_length=2,
        choices=MENTION_CHOICES,
        verbose_name="Mention",
    )
    appreciation = models.TextField(blank=True, default="", verbose_name="Appreciation libre")
    absences_count = models.PositiveSmallIntegerField(default=0, verbose_name="Nb absences sur la periode")
    surah_memorized_count = models.PositiveSmallIntegerField(default=0, verbose_name="Nb sourates memorisees")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="grades_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Appreciation"
        verbose_name_plural = "Appreciations"
        db_table = "school_grade"
        unique_together = [("child", "period")]
        ordering = ["period__order", "child__first_name"]

    def __str__(self):
        return f"{self.child.first_name} — {self.period.name} — {self.mention}"
