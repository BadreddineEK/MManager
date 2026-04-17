"""
Vues CRUD paiements cotisations
GET/POST   /api/membership/payments/
GET/PUT/PATCH/DELETE /api/membership/payments/<id>/
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import HasMosquePermission
from core.utils import get_mosque
from .models import MembershipPayment
from .serializers import MembershipPaymentSerializer


class MembershipPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipPaymentSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["member", "membership_year", "method", "status"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        return MembershipPayment.objects.filter(mosque=mosque).select_related(
            "member", "membership_year"
        )

    def perform_create(self, serializer):
        mosque = get_mosque(self.request)
        serializer.save(mosque=mosque)
        # Signal auto-cree TreasuryTransaction si method != virement

    def perform_update(self, serializer):
        serializer.save()
