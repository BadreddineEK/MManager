"""
Utilitaires partagés — core
============================
Fonctions réutilisables par toutes les apps (school, membership, treasury, …).
"""


def get_mosque(request):
    """
    Retourne la mosquée associée à la requête.

    - Utilisateur normal : request.mosque injecté par HasMosquePermission
    - Superuser sans mosquée assignée : prend la première mosquée disponible
      (utile pour les tests et la gestion admin)

    Retourne None si aucune mosquée n'existe du tout.
    """
    from core.models import Mosque

    mosque = getattr(request, "mosque", None)
    if mosque is not None:
        return mosque
    # Superuser fallback
    return Mosque.objects.first()
