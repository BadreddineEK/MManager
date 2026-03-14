"""
Vues school -- API REST Ecole coranique
=========================================
Toutes les vues filtrent automatiquement par request.mosque (multi-tenant).
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


class SchoolYearViewSet(viewsets.ModelViewSet):
    """CRUD annees scolaires -- filtre par mosquee."""

    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get_queryset(self):
        mosque = self.request.mosque
        if mosque is None:
            return SchoolYear.objects.all()
        return SchoolYear.objects.filter(mosque=mosque)

    def perform_create(self, serializer):
        serializer.save(mosque=self.request.mosque)


class FamilyViewSet(viewsets.ModelViewSet):
    """CRUD familles -- filtre par mosquee + recherche."""

    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["primary_contact_name", "email", "phone1"]
    ordering_fields = ["primary_contact_name", "created_at"]

    def get_queryset(self):
        mosque = self.request.mosque
        qs = Family.objects.prefetch_related("children", "payments")
        if mosque is None:
            return qs.all()
        return qs.filter(mosque=mosque)

    def perform_create(self, serializer):
        serializer.save(mosque=self.request.mosque)

    @action(detail=False, methods=["get"], url_path="arrears")
    def arrears(self, request):
        """
        GET /api/school/families/arrears/
        Retourne les familles qui n'ont aucun paiement pour l'annee active.
        """
        mosque = request.mosque
        # Trouver l'annee active
        active_year = SchoolYear.objects.filter(
            mosque=mosque, is_active=True
        ).first()

        if not active_year:
            return Response(
                {"detail": "Aucune annee scolaire active trouvee."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Familles ayant paye pour l'annee active
        paid_family_ids = SchoolPayment.objects.filter(
            mosque=mosque, school_year=active_year
        ).values_list("family_id", flat=True)

        # Familles sans paiement
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
    """CRUD enfants -- filtre par mosquee + niveau."""

    serializer_class = ChildSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "family__primary_contact_name"]
    ordering_fields = ["first_name", "level", "created_at"]

    def get_queryset(self):
        mosque = self.request.mosque
        qs = Child.objects.select_related("family")
        if mosque is None:
            qs = qs.all()
        else:
            qs = qs.filter(mosque=mosque)

        # Filtre optionnel par niveau : ?level=N1
        level = self.request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)

        return qs

    def perform_create(self, serializer):
        serializer.save(mosque=self.request.mosque)


class SchoolPaymentViewSet(viewsets.ModelViewSet):
    """CRUD paiements ecole -- filtre par mosquee + annee."""

    serializer_class = SchoolPaymentSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        mosque = self.request.mosque
        qs = SchoolPayment.objects.select_related("family", "child", "school_year")
        if mosque is None:
            qs = qs.all()
        else:
            qs = qs.filter(mosque=mosque)

        # Filtre optionnel par annee : ?year_id=1
        year_id = self.request.query_params.get("year_id")
        if year_id:
            qs = qs.filter(school_year_id=year_id)

        # Filtre optionnel par famille : ?family_id=2
        family_id = self.request.query_params.get("family_id")
        if family_id:
            qs = qs.filter(family_id=family_id)

        return qs

    def perform_create(self, serializer):
        serializer.save(mosque=self.request.mosque)
