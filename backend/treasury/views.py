"""
Vues Tresorerie -- API REST transactions financieres
=====================================================
"""
from django.db.models import Q, Sum
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import HasMosquePermission

from .models import TreasuryTransaction
from .serializers import TreasuryTransactionSerializer


def get_mosque(request):
    from core.models import Mosque
    mosque = getattr(request, 'mosque', None)
    if mosque is not None:
        return mosque
    return Mosque.objects.first()


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

        return qs

    def perform_create(self, serializer):
        serializer.save(mosque=get_mosque(self.request))

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/treasury/transactions/summary/
        Params optionnels : ?month=2025-03  ou  ?year=2025
        Retourne : total_in, total_out, balance, par categorie
        """
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquee trouvee."}, status=status.HTTP_404_NOT_FOUND)

        qs = TreasuryTransaction.objects.filter(mosque=mosque)

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

        return Response({
            "total_in": float(total_in),
            "total_out": float(total_out),
            "balance": float(balance),
            "categories": categories,
        })
