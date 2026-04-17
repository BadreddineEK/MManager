"""
Vues CRUD paiements cotisations
GET/POST   /api/membership/payments/
GET/PUT/PATCH/DELETE /api/membership/payments/<id>/
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import HasMosquePermission
from core.utils import get_mosque, log_action
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
        obj = serializer.save(mosque=mosque)
        log_action(self.request, "CREATE", "MembershipPayment", obj.id, {
            "member": str(obj.member),
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
        log_action(self.request, "UPDATE", "MembershipPayment", obj.id, {
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
        log_action(self.request, "DELETE", "MembershipPayment", instance.id, {
            "member": str(instance.member),
            "amount": str(instance.amount),
            "method": instance.method,
            "date": str(instance.date),
        })
        instance.delete()
