"""Configuration des URLs principales — Mosquée Manager."""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health_check(request: "django.http.HttpRequest") -> JsonResponse:
    """Point de contrôle santé — utilisé par Docker, load balancers, Cloudflare."""
    return JsonResponse({"status": "ok", "service": "mosque-manager"})


urlpatterns = [
    # Admin Django
    path("admin/", admin.site.urls),
    # Health check (aucune auth requise)
    path("health/", health_check, name="health_check"),
    # Auth JWT
    path("api/auth/", include("core.urls", namespace="core")),
    # School
    path("api/school/", include("school.urls", namespace="school")),
    # Membership
    path("api/membership/", include("membership.urls", namespace="membership")),
    # Treasury
    path("api/treasury/", include("treasury.urls", namespace="treasury")),
    # KPI (public, sans auth)
    path("api/kpi/", include("kpi.urls", namespace="kpi")),
]

