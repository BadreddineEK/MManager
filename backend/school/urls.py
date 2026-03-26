"""URLs school -- Routes API ecole coranique."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChildViewSet, FamilyViewSet, SchoolPaymentViewSet, SchoolYearViewSet
from .receipt_views import SchoolPaymentReceiptView

router = DefaultRouter()
router.register("years", SchoolYearViewSet, basename="school-year")
router.register("families", FamilyViewSet, basename="family")
router.register("children", ChildViewSet, basename="child")
router.register("payments", SchoolPaymentViewSet, basename="school-payment")

app_name = "school"
urlpatterns = router.urls + [
    path("payments/<int:pk>/receipt/", SchoolPaymentReceiptView.as_view(), name="school-payment-receipt"),
]
