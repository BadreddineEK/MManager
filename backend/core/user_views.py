"""
Vues — Gestion des utilisateurs (étape 10)
===========================================
GET    /api/users/        → liste des users de la mosquée  (ADMIN)
POST   /api/users/        → créer un user                  (ADMIN)
GET    /api/users/<id>/   → détail d'un user               (ADMIN)
PUT    /api/users/<id>/   → modifier un user               (ADMIN)
DELETE /api/users/<id>/   → supprimer un user              (ADMIN)
GET    /api/users/me/     → profil de l'utilisateur connecté (tous)
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminRole
from core.utils import get_mosque, log_action

from .models import User
from .user_serializers import UserCreateSerializer, UserListSerializer, UserUpdateSerializer

logger = logging.getLogger("core")


class UserMeView(APIView):
    """
    GET /api/users/me/
    Retourne le profil de l'utilisateur connecté (tous rôles).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserListSerializer(request.user)
        return Response(serializer.data)


class UserListCreateView(APIView):
    """
    GET  /api/users/   → liste des utilisateurs de la mosquée (ADMIN)
    POST /api/users/   → créer un utilisateur (ADMIN)
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            # Superuser : tous les users
            users = User.objects.select_related("mosque").order_by("username")
        else:
            users = User.objects.filter(mosque=mosque).select_related("mosque").order_by("username")
        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        mosque = get_mosque(request)
        # On injecte la mosquée dans le contexte du serializer
        ctx = {**self.get_renderer_context(), "request": request}
        ctx["request"].mosque = mosque  # type: ignore[attr-defined]
        serializer = UserCreateSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        log_action(request, "CREATE", "User", user.id, {"username": user.username, "role": user.role})
        logger.info("USER: créé %s (%s) par %s", user.username, user.role, request.user.username)
        return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    """
    GET    /api/users/<id>/  → détail
    PUT    /api/users/<id>/  → modifier
    DELETE /api/users/<id>/  → supprimer
    ADMIN uniquement. Un ADMIN ne peut modifier que les users de sa mosquée.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    def _get_user(self, request, user_id: int):
        """Retourne le user s'il appartient à la même mosquée, sinon 404."""
        mosque = get_mosque(request)
        try:
            if mosque is None:
                return User.objects.select_related("mosque").get(pk=user_id)
            return User.objects.select_related("mosque").get(pk=user_id, mosque=mosque)
        except User.DoesNotExist:
            return None

    def get(self, request, user_id: int):
        user = self._get_user(request, user_id)
        if user is None:
            return Response({"detail": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserListSerializer(user).data)

    def put(self, request, user_id: int):
        user = self._get_user(request, user_id)
        if user is None:
            return Response({"detail": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
        # Empêcher un ADMIN de modifier un superuser
        if user.is_superuser and not request.user.is_superuser:
            return Response({"detail": "Impossible de modifier un superutilisateur."}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        updated = serializer.save()
        log_action(request, "UPDATE", "User", updated.id, {"username": updated.username, "role": updated.role})
        logger.info("USER: modifié %s par %s", updated.username, request.user.username)
        return Response(UserListSerializer(updated).data)

    def delete(self, request, user_id: int):
        user = self._get_user(request, user_id)
        if user is None:
            return Response({"detail": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
        # Empêcher l'auto-suppression et la suppression d'un superuser
        if user.pk == request.user.pk:
            return Response({"detail": "Vous ne pouvez pas supprimer votre propre compte."}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_superuser and not request.user.is_superuser:
            return Response({"detail": "Impossible de supprimer un superutilisateur."}, status=status.HTTP_403_FORBIDDEN)
        username = user.username
        role = user.role
        uid = user.id
        user.delete()
        log_action(request, "DELETE", "User", uid, {"username": username, "role": role})
        logger.info("USER: supprimé %s par %s", username, request.user.username)
        return Response(status=status.HTTP_204_NO_CONTENT)
