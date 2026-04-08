"""
Vues API — Personnel (Staff)
=============================
GET    /api/settings/staff/        -> liste du personnel
POST   /api/settings/staff/        -> créer un membre
PUT    /api/settings/staff/<id>/   -> modifier un membre
DELETE /api/settings/staff/<id>/   -> supprimer un membre
"""
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
