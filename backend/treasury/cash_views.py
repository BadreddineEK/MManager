"""
API Stock Caisse — Pointages de billets/pièces
================================================
GET  /api/treasury/cash-counts/          → liste des pointages (20 derniers)
POST /api/treasury/cash-counts/          → créer un pointage avec ses lignes
GET  /api/treasury/cash-counts/<pk>/     → détail d'un pointage
DELETE /api/treasury/cash-counts/<pk>/   → supprimer un pointage

Permissions : IsAuthenticated + HasMosquePermission + IsTresorierRole
"""
from django.db import transaction as db_transaction
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission, IsTresorierRole

from .models import CashCount, CashDenomination


# ── Serializers ────────────────────────────────────────────────────────────────

class CashDenominationSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CashDenomination
        fields = ["id", "denomination", "quantity", "subtotal"]

    def get_subtotal(self, obj):
        return float(obj.denomination) * obj.quantity


class CashCountSerializer(serializers.ModelSerializer):
    lines = CashDenominationSerializer(many=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = CashCount
        fields = ["id", "date", "note", "created_by", "created_at", "lines", "total"]
        read_only_fields = ["id", "created_at", "total"]

    def get_total(self, obj):
        return float(obj.total)

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        mosque = self.context["mosque"]
        cash_count = CashCount.objects.create(mosque=mosque, **validated_data)
        for line in lines_data:
            if line.get("quantity", 0) > 0:
                CashDenomination.objects.create(cash_count=cash_count, **line)
        return cash_count


# ── Views ──────────────────────────────────────────────────────────────────────

class CashCountListView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsTresorierRole]

    def get(self, request):
        qs = CashCount.objects.filter(mosque=request.mosque).prefetch_related("lines")[:20]
        data = CashCountSerializer(qs, many=True).data
        return Response(data)

    @db_transaction.atomic
    def post(self, request):
        serializer = CashCountSerializer(
            data=request.data,
            context={"mosque": request.mosque},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        obj = serializer.save()
        return Response(CashCountSerializer(obj).data, status=status.HTTP_201_CREATED)


class CashCountDetailView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsTresorierRole]

    def _get_object(self, pk, mosque):
        try:
            return CashCount.objects.prefetch_related("lines").get(pk=pk, mosque=mosque)
        except CashCount.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk, request.mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(CashCountSerializer(obj).data)

    def delete(self, request, pk):
        obj = self._get_object(pk, request.mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
