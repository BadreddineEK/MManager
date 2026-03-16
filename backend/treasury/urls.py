from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CampaignViewSet, TreasuryTransactionViewSet
from .receipt_views import AnnualSummaryReceiptView, TransactionReceiptView

app_name = "treasury"

router = DefaultRouter()
router.register("transactions", TreasuryTransactionViewSet, basename="transaction")
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
    path("receipt/transaction/<int:pk>/", TransactionReceiptView.as_view(), name="receipt-transaction"),
    path("receipt/annual/", AnnualSummaryReceiptView.as_view(), name="receipt-annual"),
]
