"""Plan Enforcement — Nidham
================================
1. plan_module_permission(module_name) -> Permission DRF
2. PlanLimitMixin                      -> Mixin ViewSet
3. CurrentPlanView                     -> GET /api/settings/plan/
"""
import logging
from datetime import datetime, timezone as dt_tz

from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("core")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────────────

def _get_subscription(mosque):
    """Retourne la Subscription de la mosquée (schéma public)."""
    try:
        with schema_context("public"):
            from core.models import Subscription
            return Subscription.objects.select_related("plan").get(mosque=mosque)
    except Exception:
        return None


def _get_plan(mosque):
    sub = _get_subscription(mosque)
    return sub.plan if sub else None


def _days_remaining(sub) -> int | None:
    """Calcule les jours restants sur la période/trial."""
    from django.utils import timezone
    if sub.status in ("trial", "trialing") and sub.trial_end:
        # trial_end peut être DateField ou DateTimeField
        if hasattr(sub.trial_end, "hour"):
            delta = sub.trial_end - timezone.now()
        else:
            end_dt = datetime.combine(sub.trial_end, datetime.min.time()).replace(tzinfo=dt_tz.utc)
            delta = end_dt - timezone.now()
        return max(0, delta.days)
    elif sub.current_period_end:
        end_dt = datetime.combine(sub.current_period_end, datetime.min.time()).replace(tzinfo=dt_tz.utc)
        delta = end_dt - timezone.now()
        return max(0, delta.days)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 1. Permission DRF par module
# ─────────────────────────────────────────────────────────────────────────────

def plan_module_permission(module_name: str):
    """
    Factory → classe Permission DRF.
    Bloque si module_name n'est pas dans le plan de la mosquée.

    Usage:
        permission_classes = [IsAuthenticated, HasMosquePermission,
                               plan_module_permission("school_basic")]
    """
    class _Perm(BasePermission):
        message = (
            f"Le module '{module_name}' n'est pas inclus dans votre plan. "
            "Consultez nidham.fr/pricing pour upgrader."
        )

        def has_permission(self, request, view):
            if request.user.is_superuser:
                return True
            mosque = getattr(request, "mosque", None)
            if mosque is None:
                return False
            plan = _get_plan(mosque)
            if plan is None:
                logger.warning("PLAN: aucun plan pour %s — acces accorde", mosque.name)
                return True
            allowed = plan.allows_module(module_name)
            if not allowed:
                logger.info(
                    "PLAN BLOCKED: module=%s mosque=%s plan=%s",
                    module_name, mosque.name, plan.name,
                )
            return allowed

    _Perm.__name__ = f"PlanModule_{module_name}"
    return _Perm


# ─────────────────────────────────────────────────────────────────────────────
# 2. Mixin ViewSet — limite de ressources
# ─────────────────────────────────────────────────────────────────────────────

class PlanLimitMixin:
    """
    Bloque la création si la limite du plan est atteinte.

    Utilisation :
        class FamilyViewSet(PlanLimitMixin, ModelViewSet):
            plan_limit_resource = "families"
            plan_limit_model    = Family
    """
    plan_limit_resource: str = ""
    plan_limit_model = None

    def create(self, request, *args, **kwargs):
        if self.plan_limit_resource and self.plan_limit_model:
            mosque = getattr(request, "mosque", None)
            if mosque and not request.user.is_superuser:
                plan = _get_plan(mosque)
                if plan is not None:
                    current = self.plan_limit_model.objects.count()
                    if not plan.check_limit(self.plan_limit_resource, current):
                        limit = getattr(plan, f"max_{self.plan_limit_resource}")
                        logger.info(
                            "PLAN LIMIT: %s %d/%d mosque=%s",
                            self.plan_limit_resource, current, limit, mosque.name,
                        )
                        return Response(
                            {
                                "error": "limit_reached",
                                "resource": self.plan_limit_resource,
                                "current": current,
                                "limit": limit,
                                "limit_display": plan.get_limit_display(self.plan_limit_resource),
                                "message": (
                                    f"Limite atteinte : votre plan autorise "
                                    f"{plan.get_limit_display(self.plan_limit_resource)} "
                                    f"{self.plan_limit_resource}. "
                                    "Passez au plan superieur sur nidham.fr/pricing."
                                ),
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
        return super().create(request, *args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# 3. GET /api/settings/plan/
# ─────────────────────────────────────────────────────────────────────────────

class CurrentPlanView(APIView):
    """Retourne le plan actif + usage de la mosquée connectée."""

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticated
        from core.permissions import HasMosquePermission
        return [IsAuthenticated(), HasMosquePermission()]

    def get(self, request):
        mosque = getattr(request, "mosque", None)
        if mosque is None:
            return Response({"error": "Aucune mosquee."}, status=400)

        sub = _get_subscription(mosque)
        if sub is None:
            return Response({
                "plan_name":     "free_cloud",
                "plan_display":  "Nidham Free",
                "status":        "no_subscription",
                "is_active":     False,
                "days_remaining": None,
                "modules":       ["core", "public_portal"],
                "mosque_name":   mosque.name,
            })

        plan = sub.plan
        days = _days_remaining(sub)

        return Response({
            # ── Champs plats (utilisés par le frontend sidebar/badge) ──────────
            "plan_name":      plan.name,
            "plan_display":   plan.display_name or plan.name,
            "status":         sub.status,
            "is_active":      sub.is_active,
            "days_remaining": days,
            "modules":        plan.modules or [],
            "mosque_name":    mosque.name,
            # ── Détails plan ──────────────────────────────────────────────────
            "plan": {
                "name":           plan.name,
                "display_name":   plan.display_name,
                "price_monthly":  str(plan.price_monthly),
                "price_yearly":   str(plan.price_yearly),
                "max_families":   plan.max_families,
                "max_users":      plan.max_users,
                "max_sms_month":  plan.max_sms_month,
                "modules":        plan.modules,
                "limits": {
                    "families": plan.get_limit_display("families"),
                    "users":    plan.get_limit_display("users"),
                    "sms":      plan.get_limit_display("sms_month"),
                },
            },
            # ── Détails subscription ──────────────────────────────────────────
            "subscription": {
                "status":        sub.status,
                "billing_cycle": sub.billing_cycle,
                "trial_end":     sub.trial_end.isoformat() if sub.trial_end else None,
                "period_end":    sub.current_period_end.isoformat() if sub.current_period_end else None,
                "is_active":     sub.is_active,
                "sms_used":      sub.sms_used_this_month,
                "sms_remaining": max(0, plan.max_sms_month - sub.sms_used_this_month) if plan.max_sms_month > 0 else 0,
            },
        })
