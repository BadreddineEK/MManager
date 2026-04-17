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
from core.utils import get_mosque, log_action
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
        obj = serializer.save(mosque=mosque)
        log_action(self.request, "CREATE", "SchoolPayment", obj.id, {
            "family": str(obj.family),
            "amount": str(obj.amount),
            "method": obj.method,
            "date": str(obj.date),
        })

    def perform_update(self, serializer):
        old = serializer.instance
        old_data = {
            "amount": str(old.amount),
            "method": old.method,
            "date": str(old.date),
            "status": old.status,
            "note": old.note,
        }
        obj = serializer.save()
        log_action(self.request, "UPDATE", "SchoolPayment", obj.id, {
            "before": old_data,
            "after": {
                "amount": str(obj.amount),
                "method": obj.method,
                "date": str(obj.date),
                "status": obj.status,
                "note": obj.note,
            },
        })

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "SchoolPayment", instance.id, {
            "family": str(instance.family),
            "amount": str(instance.amount),
            "method": instance.method,
            "date": str(instance.date),
        })
        instance.delete()
