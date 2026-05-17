"""URLs import bulk — migration données historiques."""
from django.urls import path

from .bulk_import_views import BulkImportView

app_name = "bulk_import"

urlpatterns = [
    path("bulk/", BulkImportView.as_view(), name="bulk-import"),
]
