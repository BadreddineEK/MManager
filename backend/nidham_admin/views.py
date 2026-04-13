"""Vues super-admin Nidham — gestion globale des tenants et plans."""
import datetime
import logging

from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Mosque, Plan, Subscription
from .permissions import IsNidhamSuperAdmin
from .serializers import (
    ChangePlanSerializer,
    MosqueAdminSerializer,
    PlanSerializer,
)

logger = logging.getLogger("nidham_admin")


# ── Statistiques globales ────────────────────────────────────────────────────

class GlobalStatsView(APIView):
    """GET /nidham-admin/stats/ — tableau de bord super-admin."""
    permission_classes = [IsAuthenticated, IsNidhamSuperAdmin]

    def get(self, request):
        with schema_context("public"):
            total_mosques = Mosque.objects.count()
            by_plan = {}
            by_status = {}
            for sub in Subscription.objects.select_related("plan").all():
                pname = sub.plan.name
                by_plan[pname] = by_plan.get(pname, 0) + 1
                by_status[sub.status] = by_status.get(sub.status, 0) + 1

        return Response({
            "total_mosques": total_mosques,
            "by_plan": by_plan,
            "by_status": by_status,
        })


# ── Gestion des mosquées ─────────────────────────────────────────────────────

class MosqueListView(APIView):
    """GET /nidham-admin/mosques/ — liste toutes les mosquées avec stats."""
    permission_classes = [IsAuthenticated, IsNidhamSuperAdmin]

    def get(self, request):
        with schema_context("public"):
            mosques = Mosque.objects.prefetch_related("subscription__plan").order_by("created_at")
            data = MosqueAdminSerializer(mosques, many=True).data
        return Response({"count": len(data), "results": data})


class MosqueDetailView(APIView):
    """GET /nidham-admin/mosques/{id}/ — détail d'une mosquée."""
    permission_classes = [IsAuthenticated, IsNidhamSuperAdmin]

    def get(self, request, mosque_id):
        with schema_context("public"):
            try:
                mosque = Mosque.objects.get(pk=mosque_id)
            except Mosque.DoesNotExist:
                return Response({"error": "Mosquée introuvable."}, status=404)
            data = MosqueAdminSerializer(mosque).data
        return Response(data)


class MosqueChangePlanView(APIView):
    """
    PUT /nidham-admin/mosques/{id}/plan/
    Changer le plan et/ou le statut subscription d'une mosquée.
    """
    permission_classes = [IsAuthenticated, IsNidhamSuperAdmin]

    def put(self, request, mosque_id):
        serializer = ChangePlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data

        with schema_context("public"):
            try:
                mosque = Mosque.objects.get(pk=mosque_id)
            except Mosque.DoesNotExist:
                return Response({"error": "Mosquée introuvable."}, status=404)

            plan = Plan.objects.get(pk=data["plan_id"])
            today = datetime.date.today()

            sub, created = Subscription.objects.get_or_create(
                mosque=mosque,
                defaults={
                    "plan": plan,
                    "status": data["status"],
                    "billing_cycle": data["billing_cycle"],
                    "current_period_start": today,
                    "current_period_end": data.get("period_end") or today + datetime.timedelta(days=30),
                    "trial_end": data.get("trial_end"),
                },
            )
            if not created:
                sub.plan = plan
                sub.status = data["status"]
                sub.billing_cycle = data["billing_cycle"]
                if data.get("trial_end"):
                    sub.trial_end = data["trial_end"]
                if data.get("period_end"):
                    sub.current_period_end = data["period_end"]
                sub.save()

            logger.info(
                "ADMIN: plan change mosque=%s → plan=%s status=%s by=%s",
                mosque.name, plan.name, sub.status, request.user.username,
            )

        return Response({
            "success": True,
            "mosque": mosque.name,
            "plan": plan.name,
            "status": sub.status,
        })


# ── Gestion des plans ─────────────────────────────────────────────────────────

class PlanListView(APIView):
    """
    GET  /nidham-admin/plans/ — liste tous les plans
    POST /nidham-admin/plans/ — créer un plan custom
    """
    permission_classes = [IsAuthenticated, IsNidhamSuperAdmin]

    def get(self, request):
        with schema_context("public"):
            plans = Plan.objects.order_by("price_monthly")
            data = PlanSerializer(plans, many=True).data
        return Response({"count": len(data), "results": data})

    def post(self, request):
        serializer = PlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        with schema_context("public"):
            plan = serializer.save()
        logger.info("ADMIN: plan cree name=%s by=%s", plan.name, request.user.username)
        return Response(PlanSerializer(plan).data, status=201)


class PlanDetailView(APIView):
    """
    GET   /nidham-admin/plans/{id}/ — détail d'un plan
    PUT   /nidham-admin/plans/{id}/ — modifier prix/limites
    DELETE /nidham-admin/plans/{id}/ — désactiver (soft delete)
    """
    permission_classes = [IsAuthenticated, IsNidhamSuperAdmin]

    def _get_plan(self, plan_id):
        try:
            return Plan.objects.get(pk=plan_id)
        except Plan.DoesNotExist:
            return None

    def get(self, request, plan_id):
        with schema_context("public"):
            plan = self._get_plan(plan_id)
            if not plan:
                return Response({"error": "Plan introuvable."}, status=404)
            return Response(PlanSerializer(plan).data)

    def put(self, request, plan_id):
        with schema_context("public"):
            plan = self._get_plan(plan_id)
            if not plan:
                return Response({"error": "Plan introuvable."}, status=404)
            serializer = PlanSerializer(plan, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(serializer.errors, status=400)
            plan = serializer.save()
            logger.info("ADMIN: plan modifie id=%s by=%s", plan_id, request.user.username)
            return Response(PlanSerializer(plan).data)

    def delete(self, request, plan_id):
        with schema_context("public"):
            plan = self._get_plan(plan_id)
            if not plan:
                return Response({"error": "Plan introuvable."}, status=404)
            if plan.subscriptions.filter(status__in=["trial", "active"]).exists():
                return Response(
                    {"error": "Impossible : des mosquées actives utilisent ce plan."},
                    status=400,
                )
            plan.is_active = False
            plan.save()
            logger.info("ADMIN: plan desactive id=%s by=%s", plan_id, request.user.username)
            return Response({"success": True, "plan": plan.name, "is_active": False})
