"""
Utilitaires partagés — core
============================
Fonctions réutilisables par toutes les apps (school, membership, treasury, …).
"""
import logging

logger = logging.getLogger("core")


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


def log_action(request, action: str, entity: str, entity_id=None, payload: dict | None = None):
    """
    Enregistre une ligne dans AuditLog.

    Usage :
        log_action(request, "CREATE", "Family", obj.id, {"name": obj.primary_contact_name})
        log_action(request, "DELETE", "Member", member_id)

    Actions standard : CREATE, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, IMPORT, SEND_NOTIF
    """
    from core.models import AuditLog

    mosque = get_mosque(request)
    if mosque is None:
        logger.warning("log_action: aucune mosquée trouvée pour %s %s#%s", action, entity, entity_id)
        return

    try:
        AuditLog.objects.create(
            mosque=mosque,
            user=request.user if request.user.is_authenticated else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            payload=payload or {},
        )
    except Exception as exc:  # noqa: BLE001
        # Ne jamais faire planter une vue à cause d'un log
        logger.error("log_action: échec enregistrement (%s %s#%s) : %s", action, entity, entity_id, exc)
