"""
Vues CRUD paiements ecole
GET/POST   /api/school/payments/
GET/PUT/PATCH/DELETE /api/school/payments/<id>/

Regles :
- method=cash/cheque/autre -> TreasuryTransaction creee automatiquement via signal
- method=virement -> pas de TreasuryTx auto (viendra de l'import bancaire)
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import HasMosquePermission
from core.utils import get_mosque
from .models import SchoolPayment
from .serializers import SchoolPaymentSerializer


class SchoolPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolPaymentSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["family", "child", "school_year", "method", "status"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        return SchoolPayment.objects.filter(mosque=mosque).select_related(
            "family", "child", "school_year"
        )

    def perform_create(self, serializer):
        mosque = get_mosque(self.request)
        serializer.save(mosque=mosque)
        # Signal treasury/signals.py cree automatiquement la TreasuryTransaction

    def perform_update(self, serializer):
        serializer.save()
        # Signal met a jour la TreasuryTransaction liee automatiquement
