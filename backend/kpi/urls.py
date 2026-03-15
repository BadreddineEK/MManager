from django.urls import path

from .views import KPIMosqueListView, KPISummaryView

app_name = "kpi"

urlpatterns = [
    path("mosques/", KPIMosqueListView.as_view(), name="mosques"),
    path("summary/", KPISummaryView.as_view(), name="summary"),
]
