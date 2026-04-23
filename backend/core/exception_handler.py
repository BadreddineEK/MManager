"""
Gestionnaire d'exceptions personnalisé — Mosquée Manager
=========================================================
Remplace le handler DRF par défaut pour garantir :
  - Toujours du JSON propre (jamais de traceback HTML)
  - Format uniforme : {"error": "...", "detail": {...}, "status_code": N}
  - Log des erreurs 500 côté serveur sans exposer l'info au client
"""
import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Handler DRF enrichi.

    Retourne toujours du JSON structuré :
      {"error": "<message humain>", "detail": <détail brut ou null>, "status_code": N}

    Pour les 500 non catchés par DRF, retourne un message générique
    sans exposer le traceback.
    """
    # Laisser DRF gérer d'abord (ValidationError, PermissionDenied, NotFound…)
    response = drf_exception_handler(exc, context)

    if response is not None:
        original_data = response.data

        if isinstance(original_data, dict) and "detail" in original_data:
            error_msg = str(original_data["detail"])
            detail = None
        elif isinstance(original_data, dict):
            error_msg = _build_validation_message(original_data)
            detail = original_data
        elif isinstance(original_data, list):
            error_msg = original_data[0] if original_data else "Erreur de validation"
            detail = original_data
        else:
            error_msg = str(original_data)
            detail = None

        response.data = {
            "error": error_msg,
            "detail": detail,
            "status_code": response.status_code,
        }
        return response

    # Exception Python non prévue → 500
    view = context.get("view")
    logger.error(
        "Unhandled exception in view %s: %s",
        view.__class__.__name__ if view else "unknown",
        exc,
        exc_info=True,
    )

    return Response(
        {
            "error": "Une erreur interne est survenue. Notre équipe a été notifiée.",
            "detail": None,
            "status_code": 500,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _build_validation_message(errors: dict) -> str:
    """Construit un message lisible depuis les erreurs de validation DRF."""
    messages = []
    for field, errs in errors.items():
        if isinstance(errs, list):
            for e in errs:
                messages.append(f"{field} : {e}")
        else:
            messages.append(f"{field} : {errs}")
    return " | ".join(messages) if messages else "Données invalides"
