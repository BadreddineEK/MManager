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

from .models import Child, Family, SchoolPayment, SchoolYear
from .serializers import (
    ChildSerializer,
    FamilySerializer,
    SchoolPaymentSerializer,
    SchoolYearSerializer,
)


def get_mosque(request):
    """
    Retourne la mosquee de la requete.
    - User normal : request.mosque (injecte par HasMosquePermission)
    - Superuser sans mosquee : prend la premiere mosquee disponible
    """
    from core.models import Mosque
    mosque = getattr(request, 'mosque', None)
    if mosque is not None:
        return mosque
    return Mosque.objects.first()


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
        serializer.save(mosque=get_mosque(self.request))

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
        serializer.save(mosque=get_mosque(self.request))


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
        family_id = self.request.query_params.get("family_id")
        if family_id:
            qs = qs.filter(family_id=family_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))
