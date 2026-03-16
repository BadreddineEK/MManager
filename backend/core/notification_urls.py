"""URLs — Notifications email."""
from django.urls import path

from .notification_views import (
    SendArrearsNotificationsView,
    SendUnpaidMembersNotificationsView,
    TestEmailView,
)

app_name = "notifications"

urlpatterns = [
    path("send-arrears/", SendArrearsNotificationsView.as_view(), name="send-arrears"),
    path("send-unpaid-members/", SendUnpaidMembersNotificationsView.as_view(), name="send-unpaid-members"),
    path("test/", TestEmailView.as_view(), name="test"),
]
