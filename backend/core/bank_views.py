"""
Vues API — Comptes bancaires & Règles de dispatch
==================================================
GET    /api/settings/bank-accounts/           -> liste des comptes bancaires
POST   /api/settings/bank-accounts/           -> créer un compte
PUT    /api/settings/bank-accounts/<id>/      -> modifier un compte
DELETE /api/settings/bank-accounts/<id>/      -> supprimer un compte

GET    /api/settings/dispatch-rules/          -> liste des règles de dispatch
POST   /api/settings/dispatch-rules/          -> créer une règle
PUT    /api/settings/dispatch-rules/<id>/     -> modifier une règle
DELETE /api/settings/dispatch-rules/<id>/     -> supprimer une règle
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission, IsAdminRole
from core.utils import get_mosque

from .bank_serializers import BankAccountSerializer, DispatchRuleSerializer
from .models import BankAccount, DispatchRule


class BankAccountListView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def get(self, request):
        mosque = get_mosque(request)
        accounts = BankAccount.objects.filter(mosque=mosque)
        return Response(BankAccountSerializer(accounts, many=True).data)

    def post(self, request):
        mosque = get_mosque(request)
        serializer = BankAccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(mosque=mosque)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankAccountDetailView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def _get_object(self, pk, mosque):
        try:
            return BankAccount.objects.get(pk=pk, mosque=mosque)
        except BankAccount.DoesNotExist:
            return None

    def get(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(BankAccountSerializer(obj).data)

    def put(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = BankAccountSerializer(obj, data=request.data, partial=True)
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


class DispatchRuleListView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def get(self, request):
        mosque = get_mosque(request)
        rules = DispatchRule.objects.filter(mosque=mosque)
        return Response(DispatchRuleSerializer(rules, many=True).data)

    def post(self, request):
        mosque = get_mosque(request)
        serializer = DispatchRuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(mosque=mosque)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DispatchRuleDetailView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdminRole]

    def _get_object(self, pk, mosque):
        try:
            return DispatchRule.objects.get(pk=pk, mosque=mosque)
        except DispatchRule.DoesNotExist:
            return None

    def get(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DispatchRuleSerializer(obj).data)

    def put(self, request, pk):
        mosque = get_mosque(request)
        obj = self._get_object(pk, mosque)
        if obj is None:
            return Response({"detail": "Introuvable."}, status=status.HTTP_404_NOT_FOUND)
        serializer = DispatchRuleSerializer(obj, data=request.data, partial=True)
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
