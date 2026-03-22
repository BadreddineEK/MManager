from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MembershipPaymentViewSet, MembershipYearViewSet, MemberViewSet
from treasury.receipt_views import MembershipPaymentReceiptView

app_name = "membership"

router = DefaultRouter()
router.register("years", MembershipYearViewSet, basename="membership-year")
router.register("members", MemberViewSet, basename="member")
router.register("payments", MembershipPaymentViewSet, basename="membership-payment")

urlpatterns = [
    path("", include(router.urls)),
    path("receipt/payment/<int:pk>/", MembershipPaymentReceiptView.as_view(), name="membership-payment-receipt"),
]
