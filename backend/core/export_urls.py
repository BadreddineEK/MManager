from django.urls import path
from .export_views import (
    ChildrenExcelView,
    FamiliesExcelView,
    FamiliesPDFView,
    MembershipPaymentsExcelView,
    MembersPDFView,
    MembersExcelView,
    SchoolPaymentsExcelView,
    SchoolPaymentsPDFView,
    TreasuryExcelView,
    TreasuryPDFView,
)

app_name = "export"

urlpatterns = [
    # École
    path("families/excel/",          FamiliesExcelView.as_view(),          name="families-excel"),
    path("families/pdf/",            FamiliesPDFView.as_view(),            name="families-pdf"),
    path("children/excel/",          ChildrenExcelView.as_view(),          name="children-excel"),
    path("school-payments/excel/",   SchoolPaymentsExcelView.as_view(),    name="school-payments-excel"),
    path("school-payments/pdf/",     SchoolPaymentsPDFView.as_view(),      name="school-payments-pdf"),
    # Adhésion
    path("members/excel/",           MembersExcelView.as_view(),           name="members-excel"),
    path("members/pdf/",             MembersPDFView.as_view(),             name="members-pdf"),
    path("membership-payments/excel/", MembershipPaymentsExcelView.as_view(), name="membership-payments-excel"),
    # Trésorerie
    path("treasury/excel/",          TreasuryExcelView.as_view(),          name="treasury-excel"),
    path("treasury/pdf/",            TreasuryPDFView.as_view(),            name="treasury-pdf"),
]
