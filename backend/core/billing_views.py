"""Billing Views — Nidham
=========================
GET /api/billing/subscription/  → plan actif + usage SMS + limites
GET /api/billing/plans/          → tous les plans publics (pricing page, pas d'auth)
GET /api/billing/usage/          → utilisation réelle (familles, users, SMS)
"""
import logging

from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("core")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_sub_and_plan(mosque):
    """Retourne (subscription, plan) depuis le schéma public."""
    try:
        with schema_context("public"):
            from core.models import Subscription
            sub = Subscription.objects.select_related("plan").get(mosque=mosque)
            return sub, sub.plan
    except Exception:
        return None, None


def _count_families(mosque):
    """Compte les familles dans le schéma de la mosquée."""
    try:
        from django.db import connection
        with schema_context(mosque.schema_name):
            # Import dynamique : si l'app school/core a un modèle Family
            from core.models import Family  # ajuster si different
            return Family.objects.count()
    except ImportError:
        return 0
    except Exception:
        return 0


def _count_users(mosque):
    """Compte les utilisateurs actifs du tenant."""
    try:
        with schema_context(mosque.schema_name):
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return User.objects.filter(is_active=True).count()
    except Exception:
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/billing/subscription/
# ─────────────────────────────────────────────────────────────────────────────

class BillingSubscriptionView(APIView):
    """Retourne l'abonnement actif de la mosquée + limites + SMS restants."""

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        from core.permissions import HasMosquePermission
        return [IsAuthenticated(), HasMosquePermission()]

    def get(self, request):
        mosque = getattr(request, "mosque", None)
        if mosque is None:
            return Response({"error": "Aucune mosquée."}, status=400)

        sub, plan = _get_sub_and_plan(mosque)
        if sub is None:
            return Response(
                {"error": "Aucun abonnement trouvé.", "code": "no_subscription"},
                status=status.HTTP_404_NOT_FOUND,
            )

        sms_remaining = (
            max(0, plan.max_sms_month - sub.sms_used_this_month)
            if plan.max_sms_month > 0
            else 0
        )

        return Response({
            "mosque": mosque.name,
            "plan": {
                "name":          plan.name,
                "display_name":  plan.display_name or plan.name,
                "description":   plan.description or "",
                "price_monthly": str(plan.price_monthly),
                "price_yearly":  str(plan.price_yearly),
                "modules":       plan.modules or [],
                "limits": {
                    "max_families":  plan.max_families,
                    "max_users":     plan.max_users,
                    "max_sms_month": plan.max_sms_month,
                    "families_display":  plan.get_limit_display("families"),
                    "users_display":     plan.get_limit_display("users"),
                    "sms_month_display": plan.get_limit_display("sms_month"),
                },
            },
            "subscription": {
                "status":         sub.status,
                "is_active":      sub.is_active,
                "billing_cycle":  sub.billing_cycle,
                "trial_end":      sub.trial_end.isoformat() if sub.trial_end else None,
                "period_end":     sub.current_period_end.isoformat() if sub.current_period_end else None,
                "sms_used":       sub.sms_used_this_month,
                "sms_remaining":  sms_remaining,
                "sms_reset_date": sub.sms_reset_date.isoformat() if sub.sms_reset_date else None,
            },
        })


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/billing/plans/
# ─────────────────────────────────────────────────────────────────────────────

class BillingPlansView(APIView):
    """
    Liste tous les plans publics actifs — pas d'authentification requise.
    Utilisé pour la page pricing (portail public nidham.fr).
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        with schema_context("public"):
            from core.models import Plan
            plans = Plan.objects.filter(
                is_public=True, is_active=True
            ).order_by("sort_order")

            data = []
            for p in plans:
                data.append({
                    "name":          p.name,
                    "display_name":  p.display_name or p.name,
                    "description":   p.description or "",
                    "price_monthly": str(p.price_monthly),
                    "price_yearly":  str(p.price_yearly),
                    "modules":       p.modules or [],
                    "limits": {
                        "max_families":       p.max_families,
                        "max_users":          p.max_users,
                        "max_sms_month":      p.max_sms_month,
                        "families_display":   p.get_limit_display("families"),
                        "users_display":      p.get_limit_display("users"),
                        "sms_month_display":  p.get_limit_display("sms_month"),
                    },
                })
        return Response(data)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/billing/usage/
# ─────────────────────────────────────────────────────────────────────────────

class BillingUsageView(APIView):
    """
    Retourne l'utilisation réelle de la mosquée :
    familles, utilisateurs actifs, SMS consommés ce mois.
    """

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        from core.permissions import HasMosquePermission
        return [IsAuthenticated(), HasMosquePermission()]

    def get(self, request):
        mosque = getattr(request, "mosque", None)
        if mosque is None:
            return Response({"error": "Aucune mosquée."}, status=400)

        sub, plan = _get_sub_and_plan(mosque)

        families_count = _count_families(mosque)
        users_count    = _count_users(mosque)
        sms_used       = sub.sms_used_this_month if sub else 0

        return Response({
            "usage": {
                "families": {
                    "current": families_count,
                    "max":     plan.max_families if plan else None,
                    "display": plan.get_limit_display("families") if plan else "—",
                    "pct":     round(families_count / plan.max_families * 100, 1)
                               if (plan and plan.max_families > 0) else None,
                },
                "users": {
                    "current": users_count,
                    "max":     plan.max_users if plan else None,
                    "display": plan.get_limit_display("users") if plan else "—",
                    "pct":     round(users_count / plan.max_users * 100, 1)
                               if (plan and plan.max_users > 0) else None,
                },
                "sms": {
                    "used":      sms_used,
                    "max":       plan.max_sms_month if plan else 0,
                    "remaining": max(0, plan.max_sms_month - sms_used)
                                 if (plan and plan.max_sms_month > 0) else 0,
                    "display":   plan.get_limit_display("sms_month") if plan else "—",
                    "pct":       round(sms_used / plan.max_sms_month * 100, 1)
                                 if (plan and plan.max_sms_month > 0) else None,
                    "reset_date": sub.sms_reset_date.isoformat()
                                  if (sub and sub.sms_reset_date) else None,
                },
            },
        })
