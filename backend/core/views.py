"""
Vues core — Authentification JWT
==================================
POST /api/auth/login   → paire access + refresh token (payload enrichi)
POST /api/auth/refresh → nouvel access token depuis un refresh token valide
POST /api/auth/logout  → blacklist le refresh token (révocation immédiate)
"""
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import MosqueTokenObtainPairSerializer

logger = logging.getLogger("core")


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login
    Body : { "username": "...", "password": "..." }

    Réponse 200 :
    {
        "access":  "<jwt>",
        "refresh": "<jwt>"
    }
    Le payload JWT inclut : email, role, mosque_id, mosque_slug.
    """

    serializer_class = MosqueTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request: Request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            logger.info(
                "AUTH: login réussi pour %s",
                request.data.get("username", "?"),
            )
        return response


class RefreshView(TokenRefreshView):
    """
    POST /api/auth/refresh
    Body : { "refresh": "<token>" }

    Réponse 200 : { "access": "<nouveau_jwt>" }
    Si ROTATE_REFRESH_TOKENS=True, un nouveau refresh token est aussi renvoyé.
    """

    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    POST /api/auth/logout
    Body : { "refresh": "<token>" }

    Blackliste le refresh token → révocation immédiate.
    L'access token expire naturellement (durée courte).

    Réponse 204 : No Content
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Le champ 'refresh' est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("AUTH: logout — token blacklisté pour user %s", request.user.email)
        except TokenError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
