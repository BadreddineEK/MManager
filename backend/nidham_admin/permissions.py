"""Permission : réservé aux superusers Nidham uniquement."""
from rest_framework.permissions import BasePermission


class IsNidhamSuperAdmin(BasePermission):
    """Seuls les superusers Django (is_superuser=True) ont accès."""
    message = "Accès réservé aux super-admins Nidham."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_superuser
        )
