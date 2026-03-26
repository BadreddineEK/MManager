"""URLs school -- Routes API ecole coranique (ressources humaines uniquement)."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ChildViewSet, FamilyViewSet, SchoolYearViewSet

router = DefaultRouter()
router.register("years", SchoolYearViewSet, basename="school-year")
router.register("families", FamilyViewSet, basename="family")
router.register("children", ChildViewSet, basename="child")

app_name = "school"
urlpatterns = router.urls

