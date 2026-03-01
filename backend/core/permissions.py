"""
Permissions DRF — Mosquée Manager
====================================
Classes de permission à appliquer dans les vues API.

HasMosquePermission  : vérifie que l'utilisateur JWT est rattaché à une mosquée
IsAdminRole          : réservé au rôle ADMIN
IsTresorierRole      : réservé au rôle TRESORIER
IsEcoleManagerRole   : réservé au rôle ECOLE_MANAGER

Usage dans une vue :
    permission_classes = [IsAuthenticated, HasMosquePermission]

Usage avec rôle spécifique :
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]
"""
import logging

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

logger = logging.getLogger("core")


class HasMosquePermission(BasePermission):
    """
    Vérifie que l'utilisateur authentifié est rattaché à une mosquée.

    - Superusers : toujours autorisés (accès admin global)
    - Users normaux : doivent avoir mosque_id non null

    Injecte `request.mosque` pour les vues.
    """

    message = "Aucune mosquée assignée à ce compte."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            request.mosque = None  # Superuser = accès global
            return True

        if not getattr(user, "mosque_id", None):
            logger.warning(
                "RBAC: user %s (id=%d) sans mosquée — accès refusé à %s",
                user.email,
                user.pk,
                request.path,
            )
            return False

        # Injecter la mosquée dans la requête
        request.mosque = user.mosque
        return True


class IsAdminRole(BasePermission):
    """Réservé aux utilisateurs avec le rôle ADMIN (ou superuser)."""

    message = "Action réservée aux administrateurs."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(user, "role", "") == "ADMIN")
        )


class IsTresorierRole(BasePermission):
    """Réservé aux utilisateurs avec le rôle TRESORIER ou ADMIN (ou superuser)."""

    message = "Action réservée aux trésoriers."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "role", "") in ("ADMIN", "TRESORIER")
            )
        )


class IsEcoleManagerRole(BasePermission):
    """Réservé aux utilisateurs avec le rôle ECOLE_MANAGER ou ADMIN (ou superuser)."""

    message = "Action réservée aux gestionnaires école."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or getattr(user, "role", "") in ("ADMIN", "ECOLE_MANAGER")
            )
        )
