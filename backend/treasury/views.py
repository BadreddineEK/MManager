"""
Vues Tresorerie -- API REST transactions financieres + cagnottes
"""
import csv
from datetime import date, timedelta

from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
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

        # Filtrer par compte bancaire
        bank_account_id = self.request.query_params.get("bank_account")
        if bank_account_id:
            try:
                qs = qs.filter(bank_account_id=int(bank_account_id))
            except ValueError:
                pass

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

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """
        GET /api/treasury/transactions/dashboard/
        Retourne solde global, solde par compte, 12 mois, top catégories, stock caisse.
        """
        from core.models import BankAccount
        from .models import CashCount

        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquée trouvée."}, status=404)

        qs = TreasuryTransaction.objects.filter(mosque=mosque)

        total_in  = float(qs.filter(direction="IN").aggregate(s=Sum("amount"))["s"] or 0)
        total_out = float(qs.filter(direction="OUT").aggregate(s=Sum("amount"))["s"] or 0)

        accounts = BankAccount.objects.filter(mosque=mosque, is_active=True)
        by_account = []
        for acc in accounts:
            acc_qs = qs.filter(bank_account=acc)
            a_in  = float(acc_qs.filter(direction="IN").aggregate(s=Sum("amount"))["s"] or 0)
            a_out = float(acc_qs.filter(direction="OUT").aggregate(s=Sum("amount"))["s"] or 0)
            by_account.append({
                "id": acc.id, "label": acc.label, "bank_name": acc.bank_name,
                "regime": acc.regime, "balance": round(a_in - a_out, 2),
                "total_in": round(a_in, 2), "total_out": round(a_out, 2),
            })
        cash_qs = qs.filter(bank_account__isnull=True)
        cash_in  = float(cash_qs.filter(direction="IN").aggregate(s=Sum("amount"))["s"] or 0)
        cash_out = float(cash_qs.filter(direction="OUT").aggregate(s=Sum("amount"))["s"] or 0)
        if cash_in or cash_out:
            by_account.append({
                "id": None, "label": "Espèces", "bank_name": "", "regime": "",
                "balance": round(cash_in - cash_out, 2),
                "total_in": round(cash_in, 2), "total_out": round(cash_out, 2),
            })

        cutoff = date.today().replace(day=1) - timedelta(days=335)
        monthly_qs = (
            qs.filter(date__gte=cutoff)
            .annotate(month=TruncMonth("date"))
            .values("month", "direction")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        monthly = {}
        for row in monthly_qs:
            key = row["month"].strftime("%Y-%m")
            if key not in monthly:
                monthly[key] = {"month": key, "in": 0.0, "out": 0.0}
            if row["direction"] == "IN":
                monthly[key]["in"] = round(float(row["total"]), 2)
            else:
                monthly[key]["out"] = round(float(row["total"]), 2)
        monthly_list = sorted(monthly.values(), key=lambda x: x["month"])

        cat_qs = (
            qs.filter(date__gte=cutoff)
            .values("category", "direction")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        top_in, top_out = [], []
        for row in cat_qs:
            entry = {"category": row["category"], "total": round(float(row["total"]), 2)}
            if row["direction"] == "IN":
                top_in.append(entry)
            else:
                top_out.append(entry)

        last_cash = CashCount.objects.filter(mosque=mosque).order_by("-date").first()
        cash_stock = None
        if last_cash:
            cash_stock = {
                "date": str(last_cash.date),
                "total": float(last_cash.total),
                "note": last_cash.note or "",
            }

        return Response({
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "balance": round(total_in - total_out, 2),
            "by_account": by_account,
            "monthly": monthly_list,
            "top_in": top_in[:5],
            "top_out": top_out[:5],
            "cash_stock": cash_stock,
        })

    @action(detail=False, methods=["get"], url_path="export")
    def export_csv(self, request):
        """
        GET /api/treasury/transactions/export/
        Exporte les transactions filtrées en CSV (mêmes filtres que la liste).
        """
        qs = self.get_queryset().order_by("-date")
        response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
        writer = csv.writer(response, delimiter=";")
        writer.writerow(["Date", "Libellé", "Direction", "Catégorie", "Montant (€)",
                         "Méthode", "Régime", "Compte bancaire", "Note"])
        for tx in qs:
            writer.writerow([
                str(tx.date), tx.label,
                "Entrée" if tx.direction == "IN" else "Sortie",
                tx.get_category_display(),
                str(tx.amount).replace(".", ","),
                tx.get_method_display(),
                tx.regime_fiscal or "",
                tx.bank_account.label if tx.bank_account else "Espèces",
                tx.note or "",
            ])
        return response
