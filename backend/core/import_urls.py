"""URLs import en masse — CSV/Excel."""
from django.urls import path

from .import_views import ImportMembersView, ImportSchoolView, ImportTransactionsView

app_name = "import"

urlpatterns = [
    path("transactions/", ImportTransactionsView.as_view(), name="import-transactions"),
    path("members/", ImportMembersView.as_view(), name="import-members"),
    path("school/", ImportSchoolView.as_view(), name="import-school"),
]
