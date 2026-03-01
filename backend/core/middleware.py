"""
Middleware RBAC — Mosquée Manager
==================================
Injecte `request.mosque` pour les vues DRF après décodage JWT.

Note d'architecture :
  Le middleware Django s'exécute AVANT l'authentification DRF (qui se fait
  dans la vue elle-même). Le middleware ne peut donc pas vérifier le JWT.

  Ce middleware se contente d'injecter `request.mosque` quand l'utilisateur
  est déjà authentifié via session (admin Django).

  La vérification "user authentifié JWT + mosque_id valide" est assurée par
  la permission DRF `HasMosquePermission` (core/permissions.py), appliquée
  dans chaque vue API.

Exclusions :
  - Routes publiques : /health/, /admin/, /api/auth/
  - Méthodes OPTIONS (CORS preflight)
"""
import logging
from typing import Callable

from django.http import HttpRequest

logger = logging.getLogger("core")

# Préfixes d'URL exemptés du contrôle RBAC
EXEMPT_PREFIXES: tuple[str, ...] = (
    "/health/",
    "/admin/",
    "/api/auth/",
    "/static/",
)


class MosqueRBACMiddleware:
    """
    Middleware d'isolation multi-tenant.

    Pour les utilisateurs déjà authentifiés (session Django admin) :
    - Injecte `request.mosque` pour les vues

    Pour les routes /api/** protégées par JWT :
    - La vérification est déléguée à la permission DRF `HasMosquePermission`
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Laisser passer les preflight CORS
        if request.method == "OPTIONS":
            return self.get_response(request)

        # Injecter request.mosque si l'utilisateur est déjà authentifié (session)
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_superuser:
            request.mosque = getattr(user, "mosque", None)
        else:
            request.mosque = None

        return self.get_response(request)
