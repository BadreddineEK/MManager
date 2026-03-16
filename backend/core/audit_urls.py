"""URLs — Audit Log."""
from django.urls import path

from .audit_views import AuditLogListView

app_name = "audit"

urlpatterns = [
    path("", AuditLogListView.as_view(), name="list"),
]
