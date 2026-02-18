"""Configuration de l'application core — Mosquée Manager."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Application principale : gestion des utilisateurs, mosquées, paramètres.
    Les modèles complets (Mosque, MosqueSettings, AuditLog) sont ajoutés à l'étape 2.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Core — Gestion mosquée"
