"""Plan Enforcement — Nidham
================================
1. plan_module_permission(module_name) -> classe Permission DRF
2. PlanLimitMixin                      -> mixin de vue (cree)
3. CurrentPlanView                     -> GET /api/settings/plan/
"""
import logging

from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger("core")


def _get_subscription(mosque):
    try:
        with schema_context("public"):
            from core.models import Subscription
            return Subscription.objects.select_related("plan").get(mosque=mosque)
    except Exception:
        return None


def _get_plan(mosque):
    sub = _get_subscription(mosque)
    return sub.plan if sub else None


def plan_module_permission(module_name: str):
    """
    Factory -> classe Permission DRF.
    Bloque l'acces si module_name n'est pas dans le plan de la mosquee.

    Usage:
        permission_classes = [IsAuthenticated, HasMosquePermission,
                               plan_module_permission("school")]
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
                logger.info("PLAN BLOCKED: module=%s mosque=%s plan=%s",
                            module_name, mosque.name, plan.name)
            return allowed

    _Perm.__name__ = f"PlanModule_{module_name}"
    return _Perm


class PlanLimitMixin:
    """
    Mixin ViewSet — bloque la creation si limite plan atteinte.

    Definir sur la vue :
        plan_limit_resource = "families"   # nom du champ max_XXX sur Plan
        plan_limit_model    = Family       # modele a compter

    Exemple :
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
                        logger.info("PLAN LIMIT: %s %d/%d mosque=%s",
                                    self.plan_limit_resource, current, limit, mosque.name)
                        return Response(
                            {
                                "error": "limit_reached",
                                "resource": self.plan_limit_resource,
                                "current": current,
                                "limit": limit,
                                "message": (
                                    f"Limite atteinte : votre plan autorise {limit} "
                                    f"{self.plan_limit_resource}. "
                                    "Passez au plan superieur sur nidham.fr/pricing."
                                ),
                            },
                            status=status.HTTP_403_FORBIDDEN,
                        )
        return super().create(request, *args, **kwargs)


class CurrentPlanView(APIView):
    """GET /api/settings/plan/ — infos plan + subscription de la mosquee."""
    from rest_framework.permissions import IsAuthenticated as _IsAuth

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
                "plan_name": "free", "status": "no_subscription",
                "modules": [], "days_remaining": None, "mosque_name": mosque.name,
            })
        plan = sub.plan
        # Calcul des jours restants (essai ou période)
        from django.utils import timezone
        days_remaining = None
        if sub.status == "trial" and sub.trial_end:
            delta = sub.trial_end - timezone.now()
            days_remaining = max(0, delta.days)
        elif sub.current_period_end:
            from datetime import datetime, timezone as tz
            end_dt = datetime.combine(sub.current_period_end, datetime.min.time()).replace(tzinfo=tz.utc)
            delta = end_dt - timezone.now()
            days_remaining = max(0, delta.days)
        return Response({
            # Champs plats pour le frontend
            "plan_name":      plan.name,
            "plan_display":   getattr(plan, "get_name_display", lambda: plan.name)(),
            "status":         sub.status,
            "is_active":      sub.is_active,
            "days_remaining": days_remaining,
            "modules":        plan.modules or [],
            "mosque_name":    mosque.name,
            # Détails plan
            "plan": {
                "name":          plan.name,
                "price_monthly": str(plan.price_monthly),
                "price_yearly":  str(plan.price_yearly),
                "max_families":  plan.max_families,
                "max_users":     plan.max_users,
                "max_sms_month": plan.max_sms_month,
                "modules":       plan.modules,
            },
            "subscription": {
                "status":        sub.status,
                "billing_cycle": sub.billing_cycle,
                "trial_end":     sub.trial_end.isoformat() if sub.trial_end else None,
                "period_end":    sub.current_period_end.isoformat() if sub.current_period_end else None,
                "is_active":     sub.is_active,
            },
        })
