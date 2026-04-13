from django.urls import path
from .views import CheckSlugView, RegisterMosqueView

app_name = 'onboarding'

urlpatterns = [
    path('register/',   RegisterMosqueView.as_view(), name='register'),
    path('check-slug/', CheckSlugView.as_view(),      name='check_slug'),
]
