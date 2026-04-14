"""URLs school — Routes API ecole coranique."""
from django.urls import path
from rest_framework.routers import DefaultRouter

# Vues v1 (inchangees)
from .views import ChildViewSet, FamilyViewSet, SchoolYearViewSet

# Vues v2 (nouveaux)
from .views_v2 import (
    AttendanceSessionViewSet,
    ChildAbsencesView,
    ClassViewSet,
    GradePeriodViewSet,
    QuranProgressView,
)

app_name = "school"

router = DefaultRouter()
# v1
router.register("years",    SchoolYearViewSet,         basename="school-year")
router.register("families", FamilyViewSet,             basename="family")
router.register("children", ChildViewSet,              basename="child")
# v2
router.register("classes",  ClassViewSet,              basename="class")
router.register("sessions", AttendanceSessionViewSet,  basename="session")
router.register("periods",  GradePeriodViewSet,        basename="period")

urlpatterns = router.urls + [
    # Suivi Coran
    path(
        "children/<int:child_id>/quran/",
        QuranProgressView.as_view(),
        name="child-quran",
    ),
    path(
        "children/<int:child_id>/quran/<int:surah_number>/",
        QuranProgressView.as_view(),
        name="child-quran-surah",
    ),
    # Absences
    path(
        "children/<int:child_id>/absences/",
        ChildAbsencesView.as_view(),
        name="child-absences",
    ),
]
