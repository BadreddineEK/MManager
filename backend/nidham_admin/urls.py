"""URLs super-admin Nidham."""
from django.urls import path
from .views import (
    GlobalStatsView,
    MosqueChangePlanView,
    MosqueDetailView,
    MosqueListView,
    PlanDetailView,
    PlanListView,
)

app_name = "nidham_admin"

urlpatterns = [
    # Stats globales
    path("stats/",                      GlobalStatsView.as_view(),       name="stats"),
    # Mosquées
    path("mosques/",                    MosqueListView.as_view(),         name="mosque-list"),
    path("mosques/<int:mosque_id>/",    MosqueDetailView.as_view(),       name="mosque-detail"),
    path("mosques/<int:mosque_id>/plan/", MosqueChangePlanView.as_view(), name="mosque-change-plan"),
    # Plans
    path("plans/",                      PlanListView.as_view(),           name="plan-list"),
    path("plans/<int:plan_id>/",        PlanDetailView.as_view(),         name="plan-detail"),
]
