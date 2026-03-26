"""
Vues Tresorerie -- API REST transactions financieres + cagnottes
"""
from django.db.models import Q, Sum
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import HasMosquePermission
from core.utils import get_mosque, log_action

from .models import Campaign, TreasuryTransaction
from .serializers import CampaignSerializer, TreasuryTransactionSerializer


class CampaignViewSet(viewsets.ModelViewSet):
    """CRUD cagnottes / collectes."""

    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return Campaign.objects.none()
        qs = Campaign.objects.filter(mosque=mosque)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "Campaign", obj.id, {"name": obj.name})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "Campaign", obj.id, {"name": obj.name})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "Campaign", instance.id, {"name": instance.name})
        instance.delete()


class TreasuryTransactionViewSet(viewsets.ModelViewSet):
    """CRUD transactions de tresorerie + endpoint resume mensuel."""

    serializer_class = TreasuryTransactionSerializer
    permission_classes = [IsAuthenticated, HasMosquePermission]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["date", "amount", "created_at"]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return TreasuryTransaction.objects.none()
        qs = TreasuryTransaction.objects.filter(mosque=mosque)

        # Filtres optionnels
        direction = self.request.query_params.get("direction")
        if direction in ("IN", "OUT"):
            qs = qs.filter(direction=direction)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        month = self.request.query_params.get("month")   # format: 2025-03
        if month:
            try:
                year, m = month.split("-")
                qs = qs.filter(date__year=int(year), date__month=int(m))
            except (ValueError, AttributeError):
                pass

        year_param = self.request.query_params.get("year")
        if year_param:
            try:
                qs = qs.filter(date__year=int(year_param))
            except ValueError:
                pass

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(Q(label__icontains=search) | Q(note__icontains=search))

        # Filtrer par cagnotte spécifique ou toutes les tx liées à une cagnotte
        campaign_id = self.request.query_params.get("campaign")
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)
        elif self.request.query_params.get("has_campaign"):
            qs = qs.filter(campaign__isnull=False)

        # Filtrer par régime fiscal
        regime = self.request.query_params.get("regime")
        if regime in ("1901", "1905", ""):
            qs = qs.filter(regime_fiscal=regime)

        # Filtres FK école / cotisation
        family_id = self.request.query_params.get("family_id")
        if family_id:
            try:
                qs = qs.filter(family_id=int(family_id))
            except ValueError:
                pass

        school_year_id = self.request.query_params.get("school_year_id")
        if school_year_id:
            try:
                qs = qs.filter(school_year_id=int(school_year_id))
            except ValueError:
                pass

        member_id = self.request.query_params.get("member_id")
        if member_id:
            try:
                qs = qs.filter(member_id=int(member_id))
            except ValueError:
                pass

        membership_year_id = self.request.query_params.get("membership_year_id")
        if membership_year_id:
            try:
                qs = qs.filter(membership_year_id=int(membership_year_id))
            except ValueError:
                pass

        return qs

    def perform_create(self, serializer):
        obj = serializer.save(mosque=get_mosque(self.request))
        log_action(self.request, "CREATE", "TreasuryTransaction", obj.id,
                   {"label": obj.label, "amount": float(obj.amount), "direction": obj.direction})

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request, "UPDATE", "TreasuryTransaction", obj.id,
                   {"label": obj.label, "amount": float(obj.amount), "direction": obj.direction})

    def perform_destroy(self, instance):
        log_action(self.request, "DELETE", "TreasuryTransaction", instance.id,
                   {"label": instance.label, "amount": float(instance.amount)})
        instance.delete()

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/treasury/transactions/summary/
        Params optionnels : ?month=2025-03  ou  ?year=2025
        Sans paramètre : retourne le solde du mois courant.
        Avec ?total=1   : retourne le solde cumulé de toutes les transactions.
        Retourne : total_in, total_out, balance, par categorie
        """
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquee trouvee."}, status=status.HTTP_404_NOT_FOUND)

        qs = TreasuryTransaction.objects.filter(mosque=mosque)

        # Solde total (toutes transactions, sans filtre de période)
        if request.query_params.get("total"):
            total_in  = qs.filter(direction="IN").aggregate(s=Sum("amount"))["s"] or 0
            total_out = qs.filter(direction="OUT").aggregate(s=Sum("amount"))["s"] or 0
            return Response({
                "total_in":  float(total_in),
                "total_out": float(total_out),
                "balance":   float(total_in - total_out),
            })

        month = request.query_params.get("month")
        year_param = request.query_params.get("year")

        if month:
            try:
                yr, m = month.split("-")
                qs = qs.filter(date__year=int(yr), date__month=int(m))
            except (ValueError, AttributeError):
                pass
        elif year_param:
            try:
                qs = qs.filter(date__year=int(year_param))
            except ValueError:
                pass

        total_in = qs.filter(direction="IN").aggregate(s=Sum("amount"))["s"] or 0
        total_out = qs.filter(direction="OUT").aggregate(s=Sum("amount"))["s"] or 0
        balance = total_in - total_out

        # Repartition par categorie
        categories = {}
        for tx in qs.values("category", "direction", "amount"):
            cat = tx["category"]
            if cat not in categories:
                categories[cat] = {"in": 0, "out": 0}
            if tx["direction"] == "IN":
                categories[cat]["in"] += float(tx["amount"])
            else:
                categories[cat]["out"] += float(tx["amount"])

        # Repartition par régime fiscal
        regime_totals = {}
        for tx in qs.values("regime_fiscal", "direction", "amount"):
            regime = tx["regime_fiscal"] or "non_precise"
            if regime not in regime_totals:
                regime_totals[regime] = {"in": 0, "out": 0}
            if tx["direction"] == "IN":
                regime_totals[regime]["in"] += float(tx["amount"])
            else:
                regime_totals[regime]["out"] += float(tx["amount"])

        return Response({
            "total_in": float(total_in),
            "total_out": float(total_out),
            "balance": float(balance),
            "categories": categories,
            "by_regime": regime_totals,
        })
