from django.urls import path
from .settings_views import OnboardingView, SettingsStatusView, SettingsView

app_name = "settings"

urlpatterns = [
    path("", SettingsView.as_view(), name="settings"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("status/", SettingsStatusView.as_view(), name="settings-status"),
]
