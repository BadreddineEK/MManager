"""URLs school -- Routes API ecole coranique."""
from rest_framework.routers import DefaultRouter

from .views import ChildViewSet, FamilyViewSet, SchoolPaymentViewSet, SchoolYearViewSet

router = DefaultRouter()
router.register("years", SchoolYearViewSet, basename="school-year")
router.register("families", FamilyViewSet, basename="family")
router.register("children", ChildViewSet, basename="child")
router.register("payments", SchoolPaymentViewSet, basename="school-payment")

app_name = "school"
urlpatterns = router.urls
