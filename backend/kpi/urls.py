from django.urls import path

from .views import KPISummaryView

app_name = "kpi"

urlpatterns = [
    path("summary/", KPISummaryView.as_view(), name="summary"),
]
