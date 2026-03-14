from django.urls import path
from .user_views import UserDetailView, UserListCreateView, UserMeView

app_name = "users"

urlpatterns = [
    path("me/", UserMeView.as_view(), name="me"),
    path("", UserListCreateView.as_view(), name="list-create"),
    path("<int:user_id>/", UserDetailView.as_view(), name="detail"),
]
