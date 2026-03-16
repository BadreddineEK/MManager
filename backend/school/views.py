"""
Vues school -- API REST Ecole coranique
=========================================
Toutes les vues filtrent automatiquement par mosque (multi-tenant).
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import HasMosquePermission
from core.utils import get_mosque, log_action

from .models import Child, Family, SchoolPayment, SchoolYear
from .serializers import (
    ChildSerializer,
    FamilySerializer,
    SchoolPaymentSerializer,
    SchoolYearSerializer,
)


class SchoolYearViewSet(viewsets.ModelViewSet):
    """CRUD annees scolaires."""

    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return SchoolYear.objects.none()
        return SchoolYear.objects.filter(mosque=mosque)

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "SchoolYear", obj.id, {"label": obj.label})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "SchoolYear", instance.id, {"label": instance.label})
        instance.delete()


class FamilyViewSet(viewsets.ModelViewSet):
    """CRUD familles."""

    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["primary_contact_name", "email", "phone1"]
    ordering_fields = ["primary_contact_name", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        qs = Family.objects.prefetch_related("children", "payments")
        if mosque is None:
            return qs.none()
        return qs.filter(mosque=mosque)

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "Family", obj.id, {"name": obj.primary_contact_name})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Family", obj.id, {"name": obj.primary_contact_name})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Family", instance.id, {"name": instance.primary_contact_name})
        instance.delete()

    @action(detail=False, methods=["get"], url_path="arrears")
    def arrears(self, request):
        """
        GET /api/school/families/arrears/
        Retourne les familles sans paiement pour l'annee active.
        """
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquee trouvee."}, status=status.HTTP_404_NOT_FOUND)

        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()
        if not active_year:
            return Response(
                {"detail": "Aucune annee scolaire active trouvee."},
                status=status.HTTP_404_NOT_FOUND,
            )

        paid_family_ids = SchoolPayment.objects.filter(
            mosque=mosque, school_year=active_year
        ).values_list("family_id", flat=True)

        families_in_arrears = Family.objects.filter(mosque=mosque).exclude(
            id__in=paid_family_ids
        ).prefetch_related("children")

        serializer = self.get_serializer(families_in_arrears, many=True)
        return Response({
            "school_year": active_year.label,
            "count": families_in_arrears.count(),
            "families": serializer.data,
        })


class ChildViewSet(viewsets.ModelViewSet):
    """CRUD enfants."""

    serializer_class = ChildSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "family__primary_contact_name"]
    ordering_fields = ["first_name", "level", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        qs = Child.objects.select_related("family")
        if mosque is None:
            return qs.none()
        qs = qs.filter(mosque=mosque)
        level = self.request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "Child", obj.id, {"name": obj.first_name, "level": obj.level})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Child", obj.id, {"name": obj.first_name, "level": obj.level})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Child", instance.id, {"name": instance.first_name})
        instance.delete()


class SchoolPaymentViewSet(viewsets.ModelViewSet):
    """CRUD paiements ecole."""

    serializer_class = SchoolPaymentSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        qs = SchoolPayment.objects.select_related("family", "child", "school_year")
        if mosque is None:
            return qs.none()
        qs = qs.filter(mosque=mosque)
        year_id = self.request.query_params.get("year_id")
        if year_id:
            qs = qs.filter(school_year_id=year_id)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "SchoolPayment", obj.id,
                   {"family": str(obj.family), "amount": float(obj.amount), "date": str(obj.date)})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "SchoolPayment", obj.id,
                   {"family": str(obj.family), "amount": float(obj.amount)})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "SchoolPayment", instance.id,
                   {"family": str(instance.family), "amount": float(instance.amount)})
        instance.delete()
