"""URLs core — Routes d'authentification JWT."""
from django.urls import path

from .views import LoginView, LogoutView, RefreshView

app_name = "core"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
