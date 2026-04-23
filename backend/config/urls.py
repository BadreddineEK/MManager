"""Configuration des URLs principales — Mosquée Manager."""
from django.contrib import admin
from django.db import connection, OperationalError
from django.http import JsonResponse
from django.urls import include, path

APP_VERSION = "1.0.0"


def health_check(request: "django.http.HttpRequest") -> JsonResponse:
    """Point de contrôle santé — Docker, load balancers, CI/CD, UptimeRobot.
    HTTP 200 si tout va bien, HTTP 503 si la DB est inaccessible.
    """
    db_status = "ok"
    try:
        connection.ensure_connection()
    except OperationalError:
        db_status = "error"

    tenant_schema = getattr(connection, "schema_name", "unknown")
    overall = "ok" if db_status == "ok" else "degraded"

    return JsonResponse(
        {"status": overall, "db": db_status, "tenant": tenant_schema, "version": APP_VERSION},
        status=200 if overall == "ok" else 503,
    )


urlpatterns = [
    # Admin Django
    path("admin/", admin.site.urls),
    # Health check (aucune auth requise)
    path("health/", health_check, name="health_check"),
    # Auth JWT
    path("api/auth/", include("core.urls", namespace="core")),
    path("api/onboarding/", include("onboarding.urls", namespace="onboarding")),
    path("nidham-admin/", include("nidham_admin.urls", namespace="nidham_admin")),
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
    # Billing / Plans / Usage
    path("api/billing/", include("core.billing_urls", namespace="billing")),
]

