"""
Rapport mensuel tresorerie
GET /api/treasury/reports/monthly/?year=YYYY&month=MM
"""
import logging
from calendar import monthrange
from datetime import date

from django.db.models import Count, Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission
from core.utils import get_mosque
from treasury.models import Campaign, TreasuryTransaction

logger = logging.getLogger("treasury")


def _month_stats(mosque, year, month):
    qs = TreasuryTransaction.objects.filter(
        mosque=mosque, date__year=year, date__month=month,
    ).exclude(import_status="pending")
    agg = qs.aggregate(
        total_in=Sum("amount", filter=Q(direction="IN")),
        total_out=Sum("amount", filter=Q(direction="OUT")),
        count_in=Count("id", filter=Q(direction="IN")),
        count_out=Count("id", filter=Q(direction="OUT")),
    )
    total_in = float(agg["total_in"] or 0)
    total_out = float(agg["total_out"] or 0)
    return {
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "solde": round(total_in - total_out, 2),
        "count_in": agg["count_in"] or 0,
        "count_out": agg["count_out"] or 0,
    }


def _prev_month(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _delta_pct(current, previous):
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 1)


class MonthlyReportView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"error": "Mosquee introuvable."}, status=400)

        year_param = request.query_params.get("year")
        month_param = request.query_params.get("month")

        if not year_param or not month_param:
            return Response(
                {"error": "Parametres year et month obligatoires (ex: ?year=2026&month=03)."},
                status=400,
            )

        try:
            year = int(year_param)
            month = int(month_param)
            if not (1 <= month <= 12):
                raise ValueError
        except ValueError:
            return Response({"error": "Parametres year/month invalides."}, status=400)

        qs = TreasuryTransaction.objects.filter(
            mosque=mosque, date__year=year, date__month=month,
        ).exclude(import_status="pending")

        agg = qs.aggregate(
            total_in=Sum("amount", filter=Q(direction="IN")),
            total_out=Sum("amount", filter=Q(direction="OUT")),
            count_in=Count("id", filter=Q(direction="IN")),
            count_out=Count("id", filter=Q(direction="OUT")),
        )
        total_in = float(agg["total_in"] or 0)
        total_out = float(agg["total_out"] or 0)
        count_in = agg["count_in"] or 0
        count_out = agg["count_out"] or 0

        cat_in = list(
            qs.filter(direction="IN")
            .values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )
        cat_out = list(
            qs.filter(direction="OUT")
            .values("category")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )
        method_stats = list(
            qs.values("method")
            .annotate(
                total=Sum("amount"),
                count=Count("id"),
                total_in=Sum("amount", filter=Q(direction="IN")),
                total_out=Sum("amount", filter=Q(direction="OUT")),
            )
            .order_by("-total")
        )
        top_in = list(
            qs.filter(direction="IN").order_by("-amount")[:5]
            .values("id", "date", "label", "category", "amount", "method")
        )
        top_out = list(
            qs.filter(direction="OUT").order_by("-amount")[:5]
            .values("id", "date", "label", "category", "amount", "method")
        )

        prev_year, prev_month = _prev_month(year, month)
        prev = _month_stats(mosque, prev_year, prev_month)

        _, last_day = monthrange(year, month)
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)

        active_campaigns = Campaign.objects.filter(
            mosque=mosque, status="active",
        ).filter(
            Q(start_date__lte=month_end) | Q(start_date__isnull=True),
            Q(end_date__gte=month_start) | Q(end_date__isnull=True),
        ).values("id", "name", "goal_amount", "icon")

        campaigns_data = []
        for c in active_campaigns:
            collected = float(
                TreasuryTransaction.objects.filter(
                    mosque=mosque, campaign_id=c["id"], direction="IN",
                    date__year=year, date__month=month,
                ).exclude(import_status="pending")
                .aggregate(t=Sum("amount"))["t"] or 0
            )
            campaigns_data.append({
                "id": c["id"],
                "name": c["name"],
                "icon": c["icon"],
                "goal_amount": float(c["goal_amount"]) if c["goal_amount"] else None,
                "collected_this_month": round(collected, 2),
            })

        def fmt_cat(rows):
            return [{"category": r["category"], "total": round(float(r["total"]), 2), "count": r["count"]} for r in rows]

        def fmt_tx(rows):
            return [{"id": r["id"], "date": r["date"].isoformat(), "label": r["label"], "category": r["category"], "amount": float(r["amount"]), "method": r["method"]} for r in rows]

        def fmt_method(rows):
            return [{"method": r["method"], "total": round(float(r["total"]), 2), "count": r["count"], "total_in": round(float(r["total_in"] or 0), 2), "total_out": round(float(r["total_out"] or 0), 2)} for r in rows]

        return Response({
            "period": {"year": year, "month": month, "label": date(year, month, 1).strftime("%B %Y")},
            "summary": {"total_in": round(total_in, 2), "total_out": round(total_out, 2), "solde": round(total_in - total_out, 2), "count_in": count_in, "count_out": count_out},
            "vs_previous_month": {"year": prev_year, "month": prev_month, "total_in": prev["total_in"], "total_out": prev["total_out"], "solde": prev["solde"], "delta_in_pct": _delta_pct(total_in, prev["total_in"]), "delta_out_pct": _delta_pct(total_out, prev["total_out"]), "delta_solde_pct": _delta_pct(total_in - total_out, prev["solde"])},
            "breakdown_in": fmt_cat(cat_in),
            "breakdown_out": fmt_cat(cat_out),
            "by_method": fmt_method(method_stats),
            "top_transactions_in": fmt_tx(top_in),
            "top_transactions_out": fmt_tx(top_out),
            "active_campaigns": campaigns_data,
        })
