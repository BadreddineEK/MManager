"""Configuration des URLs principales — Mosquée Manager."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health_check(request: "django.http.HttpRequest") -> JsonResponse:
    """Point de contrôle santé — utilisé par Docker, load balancers, Cloudflare."""
    return JsonResponse({"status": "ok", "service": "mosque-manager"})


urlpatterns = [
    # Admin Django
    path("admin/", admin.site.urls),
    # Health check (aucune auth requise)
    path("health/", health_check, name="health_check"),
    # Les namespaces API seront ajoutés au fil des étapes :
    # path("api/auth/", include("core.urls")),
    # path("api/school/", include("school.urls")),
    # path("api/membership/", include("membership.urls")),
    # path("api/treasury/", include("treasury.urls")),
    # path("api/kpi/", include("kpi.urls")),
]
