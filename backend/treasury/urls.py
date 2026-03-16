from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CampaignViewSet, TreasuryTransactionViewSet

app_name = "treasury"

router = DefaultRouter()
router.register("transactions", TreasuryTransactionViewSet, basename="transaction")
router.register("campaigns", CampaignViewSet, basename="campaign")

urlpatterns = [
    path("", include(router.urls)),
]
