"""
Vues membership -- API REST Cotisations
=========================================
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import HasMosquePermission

from .models import Member, MembershipPayment, MembershipYear
from .serializers import (
    MemberSerializer,
    MembershipPaymentSerializer,
    MembershipYearSerializer,
)


def get_mosque(request):
    from core.models import Mosque
    mosque = getattr(request, 'mosque', None)
    if mosque is not None:
        return mosque
    return Mosque.objects.first()


class MembershipYearViewSet(viewsets.ModelViewSet):
    """CRUD annees de cotisation."""

    serializer_class = MembershipYearSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return MembershipYear.objects.none()
        return MembershipYear.objects.filter(mosque=mosque).prefetch_related("payments")

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))


class MemberViewSet(viewsets.ModelViewSet):
    """CRUD adherents."""

    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email", "phone"]
    ordering_fields = ["full_name", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return Member.objects.none()
        qs = Member.objects.filter(mosque=mosque).prefetch_related("payments")

        # Filtre ?status=paid ou ?status=unpaid
        status_filter = self.request.query_params.get("status")
        if status_filter:
            active_year = MembershipYear.objects.filter(
                mosque=mosque, is_active=True
            ).first()
            if active_year:
                paid_ids = MembershipPayment.objects.filter(
                    mosque=mosque, membership_year=active_year
                ).values_list("member_id", flat=True)
                if status_filter == "paid":
                    qs = qs.filter(id__in=paid_ids)
                elif status_filter == "unpaid":
                    qs = qs.exclude(id__in=paid_ids)
        return qs

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))

    @action(detail=False, methods=["get"], url_path="unpaid")
    def unpaid(self, request):
        """GET /api/membership/members/unpaid/ -- adherents sans cotisation annee active."""
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquee trouvee."}, status=status.HTTP_404_NOT_FOUND)

        active_year = MembershipYear.objects.filter(mosque=mosque, is_active=True).first()
        if not active_year:
            return Response(
                {"detail": "Aucune annee de cotisation active."},
                status=status.HTTP_404_NOT_FOUND,
            )

        paid_ids = MembershipPayment.objects.filter(
            mosque=mosque, membership_year=active_year
        ).values_list("member_id", flat=True)

        unpaid_members = Member.objects.filter(mosque=mosque).exclude(id__in=paid_ids)
        serializer = self.get_serializer(unpaid_members, many=True)
        return Response({
            "year": active_year.year,
            "amount_expected": float(active_year.amount_expected),
            "count": unpaid_members.count(),
            "members": serializer.data,
        })


class MembershipPaymentViewSet(viewsets.ModelViewSet):
    """CRUD paiements cotisations."""

    serializer_class = MembershipPaymentSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return MembershipPayment.objects.none()
        qs = MembershipPayment.objects.filter(mosque=mosque).select_related("member", "membership_year")

        year_id = self.request.query_params.get("year_id")
        if year_id:
            qs = qs.filter(membership_year_id=year_id)

        member_id = self.request.query_params.get("member_id")
        if member_id:
            qs = qs.filter(member_id=member_id)

        return qs

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))
