"""
URLs du schéma public (partagé entre tous les tenants).

Ces routes sont accessibles depuis n'importe quel sous-domaine
AVANT que le tenant soit activé — typiquement :
  - Authentification globale (login, refresh, logout)
  - Admin Nidham super-admin
  - Health check

Note : Les APIs métier (familles, trésorerie, école...) sont dans urls.py
       et ne sont accessibles qu'après activation du tenant.
"""
from django.contrib import admin
from django.db import connection, OperationalError
from django.http import JsonResponse
from django.urls import include, path

from config.urls import APP_VERSION


def health_check(request):
    db_status = "ok"
    try:
        connection.ensure_connection()
    except OperationalError:
        db_status = "error"
    overall = "ok" if db_status == "ok" else "degraded"
    return JsonResponse(
        {"status": overall, "db": db_status, "schema": "public", "version": APP_VERSION},
        status=200 if overall == "ok" else 503,
    )


urlpatterns = [
    # Admin Nidham (super-admin)
    path("admin/", admin.site.urls),
    # Health check
    path("health/", health_check, name="health_check_public"),
    # Auth JWT globale (accessible depuis tous les sous-domaines)
    path("api/auth/", include("core.urls", namespace="core")),
    path("api/onboarding/", include("onboarding.urls", namespace="onboarding")),
    path("nidham-admin/", include("nidham_admin.urls", namespace="nidham_admin")),
    # KPI public (ecran TV, sans auth, accessible depuis le schema public aussi)
    path("api/kpi/", include("kpi.urls", namespace="kpi")),
]
