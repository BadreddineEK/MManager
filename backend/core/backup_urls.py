"""URLs Backup / Restore — /api/backup/"""
from django.urls import path
from .backup_views import BackupExportView, BackupImportView

app_name = "backup"

urlpatterns = [
    path("export/", BackupExportView.as_view(), name="export"),
    path("import/", BackupImportView.as_view(), name="import"),
]
