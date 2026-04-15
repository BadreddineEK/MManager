"""
Vues membership -- API REST Adhérents
=========================================
Ressources humaines uniquement : adhérents, années de cotisation.
Les paiements sont dans TreasuryTransaction (category='cotisation').
"""
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import HasMosquePermission
from core.plan_enforcement import PlanLimitMixin, plan_module_permission
from core.utils import get_mosque, log_action

from .models import Member, MembershipYear
from .serializers import (
    MemberSerializer,
    MembershipYearSerializer,
)


class MembershipYearViewSet(viewsets.ModelViewSet):
    """CRUD annees de cotisation."""

    serializer_class = MembershipYearSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return MembershipYear.objects.none()
        return MembershipYear.objects.filter(mosque=mosque)

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "MembershipYear", obj.id, {"year": obj.year})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "MembershipYear", instance.id, {"year": instance.year})
        instance.delete()


class MemberViewSet(PlanLimitMixin, viewsets.ModelViewSet):
    """CRUD adhérents."""

    plan_limit_resource = "families"
    plan_limit_model = Member
    serializer_class = MemberSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["full_name", "email", "phone"]
    ordering_fields = ["full_name", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return Member.objects.none()
        qs = Member.objects.filter(mosque=mosque)

        # Filtre ?status=paid ou ?status=unpaid (lu depuis treasury)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            from treasury.models import TreasuryTransaction
            active_year = MembershipYear.objects.filter(
                mosque=mosque, is_active=True
            ).first()
            if active_year:
                paid_ids = TreasuryTransaction.objects.filter(
                    mosque=mosque,
                    category="cotisation",
                    membership_year=active_year,
                ).values_list("member_id", flat=True).distinct()
                if status_filter == "paid":
                    qs = qs.filter(id__in=paid_ids)
                elif status_filter == "unpaid":
                    qs = qs.exclude(id__in=paid_ids)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "Member", obj.id, {"name": obj.full_name})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Member", obj.id, {"name": obj.full_name})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Member", instance.id, {"name": instance.full_name})
        instance.delete()

    @action(detail=False, methods=["get"], url_path="unpaid")
    def unpaid(self, request):
        """GET /api/membership/members/unpaid/ -- adhérents sans cotisation année active."""
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquee trouvee."}, status=status.HTTP_404_NOT_FOUND)

        active_year = MembershipYear.objects.filter(mosque=mosque, is_active=True).first()
        if not active_year:
            return Response(
                {"detail": "Aucune annee de cotisation active."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from treasury.models import TreasuryTransaction
        paid_ids = TreasuryTransaction.objects.filter(
            mosque=mosque,
            category="cotisation",
            membership_year=active_year,
        ).values_list("member_id", flat=True).distinct()

        unpaid_members = Member.objects.filter(mosque=mosque).exclude(id__in=paid_ids)
        serializer = self.get_serializer(unpaid_members, many=True)
        return Response({
            "year": active_year.year,
            "amount_expected": float(active_year.amount_expected),
            "count": unpaid_members.count(),
            "members": serializer.data,
        })
