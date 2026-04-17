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
from django.http import JsonResponse
from django.urls import include, path


def health_check(request):
    return JsonResponse({"status": "ok", "service": "nidham", "schema": "public"})


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
