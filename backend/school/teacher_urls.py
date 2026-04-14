"""URLs teacher — Espace professeur (scope limite a sa classe)."""
from django.urls import path
from .teacher_views import (
    TeacherMeView,
    TeacherMyClassView,
    TeacherSessionListView,
    TeacherSessionDetailView,
    TeacherQuranView,
    TeacherChildAbsencesView,
    TeacherGradeView,
)

# Prefixe : /api/school/teacher/
teacher_urlpatterns = [
    # Profil + classes assignees
    path("teacher/me/",                              TeacherMeView.as_view(),           name="teacher-me"),
    # Eleves de mes classes
    path("teacher/my-class/",                        TeacherMyClassView.as_view(),      name="teacher-my-class"),
    # Seances d'appel
    path("teacher/sessions/",                        TeacherSessionListView.as_view(),  name="teacher-sessions"),
    path("teacher/sessions/<int:session_id>/",       TeacherSessionDetailView.as_view(), name="teacher-session-detail"),
    path("teacher/sessions/<int:session_id>/submit/",TeacherSessionDetailView.as_view(), name="teacher-session-submit"),
    # Suivi Coran (depuis espace prof)
    path("teacher/children/<int:child_id>/quran/",               TeacherQuranView.as_view(), name="teacher-child-quran"),
    path("teacher/children/<int:child_id>/quran/<int:surah_number>/", TeacherQuranView.as_view(), name="teacher-child-quran-surah"),
    # Absences
    path("teacher/children/<int:child_id>/absences/", TeacherChildAbsencesView.as_view(), name="teacher-child-absences"),
    # Appreciations
    path("teacher/periods/<int:period_id>/grades/",  TeacherGradeView.as_view(),        name="teacher-grades"),
]
