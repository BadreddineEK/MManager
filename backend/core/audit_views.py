"""
Vues Audit Log
===============
GET  /api/audit/         → liste paginée des logs (ADMIN)
     Paramètres :
       ?action=CREATE|UPDATE|DELETE|...
       ?entity=Family|Child|SchoolPayment|Member|...
       ?user_id=<id>
       ?from=YYYY-MM-DD
       ?to=YYYY-MM-DD
       ?page=1&page_size=50
"""
import logging
from datetime import datetime

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import AuditLog, User
from core.permissions import IsAdminRole
from core.utils import get_mosque

logger = logging.getLogger("core")


class AuditLogPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class AuditLogListView(APIView):
    """
    GET /api/audit/
    Retourne les logs d'audit de la mosquée, filtrables.
    Réservé aux ADMIN.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Aucune mosquée trouvée."}, status=status.HTTP_404_NOT_FOUND)

        qs = AuditLog.objects.filter(mosque=mosque).select_related("user").order_by("-created_at")

        # Filtres optionnels
        action = request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        entity = request.query_params.get("entity")
        if entity:
            qs = qs.filter(entity=entity)

        user_id = request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)

        from_date = request.query_params.get("from")
        if from_date:
            try:
                qs = qs.filter(created_at__date__gte=datetime.strptime(from_date, "%Y-%m-%d").date())
            except ValueError:
                pass

        to_date = request.query_params.get("to")
        if to_date:
            try:
                qs = qs.filter(created_at__date__lte=datetime.strptime(to_date, "%Y-%m-%d").date())
            except ValueError:
                pass

        # Pagination
        paginator = AuditLogPagination()
        page = paginator.paginate_queryset(qs, request)

        data = [
            {
                "id": log.id,
                "action": log.action,
                "entity": log.entity,
                "entity_id": log.entity_id,
                "payload": log.payload,
                "user": {
                    "id": log.user.id if log.user else None,
                    "username": log.user.username if log.user else "—",
                    "display": (
                        f"{log.user.first_name} {log.user.last_name}".strip() or log.user.username
                        if log.user else "—"
                    ),
                },
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for log in page
        ]

        return paginator.get_paginated_response(data)
