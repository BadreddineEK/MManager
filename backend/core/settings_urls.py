from django.urls import path
from .settings_views import OnboardingView, SettingsStatusView, SettingsView
from .plan_enforcement import CurrentPlanView
from .bank_views import (
    BankAccountDetailView,
    BankAccountListView,
    DispatchRuleDetailView,
    DispatchRuleListView,
)
from .staff_views import StaffDetailView, StaffHistoryView, StaffListView

app_name = "settings"

urlpatterns = [
    path("", SettingsView.as_view(), name="settings"),
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("status/", SettingsStatusView.as_view(), name="settings-status"),
    path("plan/", CurrentPlanView.as_view(), name="current-plan"),
    # Comptes bancaires
    path("bank-accounts/", BankAccountListView.as_view(), name="bank-account-list"),
    path("bank-accounts/<int:pk>/", BankAccountDetailView.as_view(), name="bank-account-detail"),
    # Regles de dispatch
    path("dispatch-rules/", DispatchRuleListView.as_view(), name="dispatch-rule-list"),
    path("dispatch-rules/<int:pk>/", DispatchRuleDetailView.as_view(), name="dispatch-rule-detail"),
    # Personnel
    path("staff/", StaffListView.as_view(), name="staff-list"),
    path("staff/<int:pk>/", StaffDetailView.as_view(), name="staff-detail"),
    path("staff/<int:pk>/history/", StaffHistoryView.as_view(), name="staff-history"),
]
