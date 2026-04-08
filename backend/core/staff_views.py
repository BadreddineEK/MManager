"""
Vues API — Personnel (Staff)
=============================
GET    /api/settings/staff/              -> liste du personnel
POST   /api/settings/staff/              -> créer un membre
GET    /api/settings/staff/<id>/         -> détail
PUT    /api/settings/staff/<id>/         -> modifier un membre
DELETE /api/settings/staff/<id>/         -> supprimer un membre
GET    /api/settings/staff/<id>/history/ -> transactions salaire liées
"""
from django.db.models import Sum
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission, IsAdminRole
from core.utils import get_mosque

from .models import Staff
from .staff_serializers import StaffSerializer


class StaffListView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def get(self, request):
        mosque = get_mosque(request)
        staff = Staff.objects.filter(mosque=mosque).order_by("-is_active", "role", "full_name")
        return Response(StaffSerializer(staff, many=True).data)

    def post(self, request):
        mosque = get_mosque(request)
        serializer = StaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(mosque=mosque)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StaffDetailView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def _get_object(self, pk, mosque):
        try:
            return Staff.objects.get(pk=pk, mosque=mosque)
        except Staff.DoesNotExist:
            return None

    def get(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StaffSerializer(obj).data)

    def put(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = StaffSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffHistoryView(APIView):
    """
    GET /api/settings/staff/<pk>/history/
    Retourne les transactions de trésorerie (salaire OUT) liées au name_keyword du membre.
    """
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def get(self, request, pk):
        from treasury.models import TreasuryTransaction

        mosque = get_mosque(request)
        try:
            member = Staff.objects.get(pk=pk, mosque=mosque)
        except Staff.DoesNotExist:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)

        txs = TreasuryTransaction.objects.filter(
            mosque=mosque, category="salaire", direction="OUT",
        ).order_by("-date")

        if member.name_keyword:
            txs = txs.filter(label__icontains=member.name_keyword)

        total_paid = float(txs.aggregate(s=Sum("amount"))["s"] or 0)

        data = [
            {
                "id": tx.id,
                "date": str(tx.date),
                "label": tx.label,
                "amount": float(tx.amount),
                "method": tx.get_method_display(),
                "note": tx.note or "",
            }
            for tx in txs[:50]
        ]

        return Response({
            "staff_id": member.id,
            "full_name": member.full_name,
            "monthly_salary": float(member.monthly_salary) if member.monthly_salary else None,
            "total_paid": round(total_paid, 2),
            "count": len(data),
            "transactions": data,
        })
