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
    path("api/onboarding/", include("onboarding.urls", namespace="onboarding")),
    # School
    path("api/school/", include("school.urls", namespace="school")),
    # Membership
    path("api/membership/", include("membership.urls", namespace="membership")),
    # Treasury
    path("api/treasury/", include("treasury.urls", namespace="treasury")),
    # KPI (public, sans auth)
    path("api/kpi/", include("kpi.urls", namespace="kpi")),
    # Settings + Onboarding (ADMIN)
    path("api/settings/", include("core.settings_urls", namespace="settings")),
    # Gestion des utilisateurs (ADMIN)
    path("api/users/", include("core.user_urls", namespace="users")),
    # Export Excel / PDF
    path("api/export/", include("core.export_urls", namespace="export")),
    # Backup / Restore (ZIP multi-CSV)
    path("api/backup/", include("core.backup_urls", namespace="backup")),
    # Audit Log (ADMIN)
    path("api/audit/", include("core.audit_urls", namespace="audit")),
    # Notifications email (ADMIN)
    path("api/notifications/", include("core.notification_urls", namespace="notifications")),
    # Import en masse CSV/Excel (ADMIN)
    path("api/import/", include("core.import_urls", namespace="import")),
]

