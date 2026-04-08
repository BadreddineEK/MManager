from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CampaignViewSet, TreasuryTransactionViewSet
from .receipt_views import (
    AnnualSummaryReceiptView,
    MembershipPaymentReceiptView,
    MemberSheetView,
    TransactionReceiptView,
)
from .bank_import_views import (
    BankImportView,
    ImportPendingDetailView,
    ImportPendingListView,
)

app_name = "treasury"

router = DefaultRouter()
router.register("transactions", TreasuryTransactionViewSet, basename="transaction")
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
    # Recus PDF
    path("receipt/transaction/<int:pk>/", TransactionReceiptView.as_view(), name="receipt-transaction"),
    path("receipt/annual/", AnnualSummaryReceiptView.as_view(), name="receipt-annual"),
    path("receipt/membership/<int:pk>/", MembershipPaymentReceiptView.as_view(), name="receipt-membership"),
    path("receipt/member/<int:pk>/", MemberSheetView.as_view(), name="receipt-member"),
    # Import bancaire CSV
    path("import/bank/", BankImportView.as_view(), name="import-bank"),
    path("import/pending/", ImportPendingListView.as_view(), name="import-pending-list"),
    path("import/pending/<int:pk>/", ImportPendingDetailView.as_view(), name="import-pending-detail"),
]
