app_name = "billing"

from django.urls import path
from core.billing_views import (
    BillingSubscriptionView,
    BillingPlansView,
    BillingUsageView,
)

urlpatterns = [
    path("subscription/", BillingSubscriptionView.as_view(), name="billing-subscription"),
    path("plans/",         BillingPlansView.as_view(),        name="billing-plans"),
    path("usage/",         BillingUsageView.as_view(),        name="billing-usage"),
]
