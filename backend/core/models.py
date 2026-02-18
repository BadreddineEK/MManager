"""
Modèles core — Étape 1 : modèle User minimal.

AUTH_USER_MODEL doit être défini avant la première migration Django.
Le modèle User est donc créé ici sous sa forme minimale.

⚠️  Étape 2 ajoutera :
    - Mosque, MosqueSettings, AuditLog
    - Champs mosque (ForeignKey) et role sur User
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Utilisateur personnalisé de Mosquée Manager.

    Hérite de AbstractUser (username, email, password, is_staff, etc.).
    Les champs `mosque` et `role` seront ajoutés à l'étape 2 une fois
    que le modèle Mosque sera disponible.
    """

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        db_table = "core_user"

    def __str__(self) -> str:
        """Représentation lisible : email en priorité, sinon username."""
        return self.email or self.username
