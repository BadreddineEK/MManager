"""
Vue KPI -- agregats mosquee (AUCUNE donnee personnelle)
=======================================================
GET /api/kpi/mosques/            → liste des mosquees (slug + nom)
GET /api/kpi/summary/?mosque=<slug>

Accessible SANS authentification (ecran TV/tablette public).
Retourne uniquement des compteurs et totaux, jamais de noms/tel/email.
"""
from datetime import date, datetime

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Mosque
from membership.models import Member, MembershipYear
from school.models import Attendance, AttendanceSession, Child, Class, ClassEnrollment, Family, SchoolYear
from treasury.models import Campaign, TreasuryTransaction


class KPIMosqueListView(APIView):
    """
    Liste publique des mosquees disponibles.
    GET /api/kpi/mosques/
    Retourne : [{slug, name}, ...]
    """
    permission_classes = [AllowAny]

    def get(self, request):
        mosques = Mosque.objects.order_by("name").values("slug", "name")
        return Response(list(mosques))


class KPISummaryView(APIView):
    """
    Agregats KPI de la mosquee -- aucun PII.

    Query params :
        mosque  (obligatoire) : slug de la mosquee
        month   (optionnel)   : format YYYY-MM, defaut = mois courant
    """

    permission_classes = [AllowAny]

    def get(self, request):
        # ── Mosquee ──────────────────────────────────────────────────────────
        slug = request.query_params.get("mosque")
        if not slug:
            return Response(
                {"detail": "Parametre 'mosque' (slug) obligatoire."},
                status=400,
            )
        mosque = get_object_or_404(Mosque, slug=slug)

        # ── Periode (mois) ───────────────────────────────────────────────────
        today = date.today()
        month_param = request.query_params.get("month")
        if month_param:
            try:
                yr, m = month_param.split("-")
                period_year, period_month = int(yr), int(m)
            except (ValueError, AttributeError):
                period_year, period_month = today.year, today.month
        else:
            period_year, period_month = today.year, today.month

        period_label = f"{period_year:04d}-{period_month:02d}"

        # ══ KPI SCHOOL ═══════════════════════════════════════════════════════
        active_year = SchoolYear.objects.filter(mosque=mosque, is_active=True).first()

        total_families = Family.objects.filter(mosque=mosque).count()
        children_qs = Child.objects.filter(mosque=mosque)
        total_children = children_qs.count()

        by_level = {}
        for child in children_qs.values("level"):
            lvl = child["level"] or "?"
            by_level[lvl] = by_level.get(lvl, 0) + 1

        amount_paid_school = 0.0
        families_paid_ids = set()
        active_year_label = None

        if active_year:
            active_year_label = active_year.label
            # Lire depuis TreasuryTransaction (source unique de vérité)
            tx_school_qs = TreasuryTransaction.objects.filter(
                mosque=mosque, school_year=active_year, category="ecole", direction="IN"
            )
            amount_paid_school = float(
                tx_school_qs.aggregate(s=Sum("amount"))["s"] or 0
            )
            families_paid_ids = set(
                tx_school_qs.filter(family__isnull=False)
                .values_list("family_id", flat=True).distinct()
            )

        families_unpaid = max(total_families - len(families_paid_ids), 0)

        # KPI École v2 — Classes, inscrits, taux de présence
        classes_count = 0
        total_enrolled = 0
        attendance_rate = None

        if active_year:
            classes_qs = Class.objects.filter(mosque=mosque, school_year=active_year)
            classes_count = classes_qs.count()
            total_enrolled = ClassEnrollment.objects.filter(
                school_class__mosque=mosque,
                school_class__school_year=active_year,
                is_active=True,
            ).count()
            # Taux de présence : dernières 30 séances de l'année active
            recent_sessions = AttendanceSession.objects.filter(
                mosque=mosque,
                school_class__school_year=active_year,
            ).order_by("-date")[:30]
            session_ids = list(recent_sessions.values_list("id", flat=True))
            if session_ids:
                total_att = Attendance.objects.filter(session_id__in=session_ids).count()
                present_att = Attendance.objects.filter(
                    session_id__in=session_ids,
                    status__in=["present", "late"],
                ).count()
                attendance_rate = round(present_att / total_att * 100, 1) if total_att else None

        # ══ KPI MEMBERSHIP ═══════════════════════════════════════════════════
        active_mbr_year = MembershipYear.objects.filter(
            mosque=mosque, is_active=True
        ).first()

        total_members = Member.objects.filter(mosque=mosque).count()
        members_paid = 0
        total_collected_mbr = 0.0
        mbr_year_label = None
        amount_expected_per_member = 0.0

        if active_mbr_year:
            mbr_year_label = active_mbr_year.year
            amount_expected_per_member = float(active_mbr_year.amount_expected)
            # Lire depuis TreasuryTransaction (source unique de vérité)
            tx_mbr_qs = TreasuryTransaction.objects.filter(
                mosque=mosque, membership_year=active_mbr_year,
                category="cotisation", direction="IN"
            )
            paid_ids = set(
                tx_mbr_qs.filter(member__isnull=False)
                .values_list("member_id", flat=True).distinct()
            )
            members_paid = len(paid_ids)
            total_collected_mbr = float(
                tx_mbr_qs.aggregate(s=Sum("amount"))["s"] or 0
            )

        members_unpaid = max(total_members - members_paid, 0)

        # ══ KPI TREASURY ═════════════════════════════════════════════════════
        tx_qs = TreasuryTransaction.objects.filter(
            mosque=mosque,
            date__year=period_year,
            date__month=period_month,
        )
        total_in = float(
            tx_qs.filter(direction="IN").aggregate(s=Sum("amount"))["s"] or 0
        )
        total_out = float(
            tx_qs.filter(direction="OUT").aggregate(s=Sum("amount"))["s"] or 0
        )
        by_category = {}
        for tx in tx_qs.values("category", "direction", "amount"):
            cat = tx["category"]
            if cat not in by_category:
                by_category[cat] = {"in": 0.0, "out": 0.0}
            if tx["direction"] == "IN":
                by_category[cat]["in"] += float(tx["amount"])
            else:
                by_category[cat]["out"] += float(tx["amount"])

        # Répartition par régime fiscal
        by_regime = {}
        for tx in tx_qs.values("regime_fiscal", "direction", "amount"):
            regime = tx["regime_fiscal"] or "non_precise"
            if regime not in by_regime:
                by_regime[regime] = {"in": 0.0, "out": 0.0}
            if tx["direction"] == "IN":
                by_regime[regime]["in"] += float(tx["amount"])
            else:
                by_regime[regime]["out"] += float(tx["amount"])

        # ── Préférences KPI (widgets + refresh) ──────────────────────────────
        kpi_prefs = {
            "show_school":     True,
            "show_membership": True,
            "show_treasury":   True,
            "show_campaigns":  True,
            "refresh_secs":    60,
        }
        try:
            s = mosque.settings
            kpi_prefs = {
                "show_school":     s.show_kpi_school,
                "show_membership": s.show_kpi_membership,
                "show_treasury":   s.show_kpi_treasury,
                "show_campaigns":  s.show_kpi_campaigns,
                "refresh_secs":    s.kpi_refresh_secs,
            }
        except Exception:
            pass

        # ── Cagnottes actives visibles KPI ───────────────────────────────────
        campaigns_qs = Campaign.objects.filter(mosque=mosque, show_on_kpi=True)
        campaigns_data = []
        for c in campaigns_qs:
            campaigns_data.append({
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "icon": c.icon,
                "goal_amount": float(c.goal_amount) if c.goal_amount else None,
                "collected_amount": c.collected_amount,
                "progress_percent": c.progress_percent,
                "status": c.status,
                "start_date": str(c.start_date) if c.start_date else None,
                "end_date": str(c.end_date) if c.end_date else None,
            })

        # ── Reponse finale (aucun PII) ────────────────────────────────────────
        return Response({
            "mosque": mosque.name,
            "generated_at": datetime.now().isoformat(),
            "school": {
                "total_families": total_families,
                "total_children": total_children,
                "by_level": by_level,
                "active_year": active_year_label,
                "amount_paid": amount_paid_school,
                "families_paid": len(families_paid_ids),
                "families_unpaid": families_unpaid,
                "classes_count": classes_count,
                "total_enrolled": total_enrolled,
                "attendance_rate": attendance_rate,
            },
            "membership": {
                "active_year": mbr_year_label,
                "amount_expected_per_member": amount_expected_per_member,
                "total_members": total_members,
                "members_paid": members_paid,
                "members_unpaid": members_unpaid,
                "total_collected": total_collected_mbr,
            },
            "treasury": {
                "period": period_label,
                "total_in": total_in,
                "total_out": total_out,
                "balance": round(total_in - total_out, 2),
                "by_category": by_category,
                "by_regime": by_regime,
            },
            "campaigns": campaigns_data,
            "kpi_prefs": kpi_prefs,
        })
