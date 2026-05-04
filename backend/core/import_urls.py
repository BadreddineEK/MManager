"""URLs import en masse — CSV/Excel."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .bank_import_views import BankImportPreviewView, BankImportProfileViewSet, BankImportView
from .import_views import ImportMembersView, ImportSchoolView, ImportTransactionsView

app_name = "import"

router = DefaultRouter()
router.register(r"bank/profiles", BankImportProfileViewSet, basename="bank-profiles")

urlpatterns = [
    path("transactions/", ImportTransactionsView.as_view(), name="import-transactions"),
    path("members/", ImportMembersView.as_view(), name="import-members"),
    path("school/", ImportSchoolView.as_view(), name="import-school"),
    # Import bancaire configurable
    path("bank/preview/", BankImportPreviewView.as_view(), name="bank-preview"),
    path("bank/", BankImportView.as_view(), name="bank-import"),
    path("", include(router.urls)),
]
