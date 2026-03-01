"""
Tests core -- Authentification JWT + Permissions RBAC
=======================================================
Couverture :
  - Login valide -> 200 + tokens
  - Login invalide -> 401
  - Login champs manquants -> 400
  - Refresh token -> 200
  - Logout -> 204
  - Logout sans refresh -> 400
  - Logout non authentifie -> 401
  - HasMosquePermission : user avec mosquee -> True
  - HasMosquePermission : user sans mosquee -> False
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Mosque, User
from .permissions import HasMosquePermission


class AuthTestCase(TestCase):
    """Tests du flux d'authentification JWT."""

    def setUp(self) -> None:
        self.client = APIClient()

        self.mosque = Mosque.objects.create(
            name="Mosquee de Test",
            slug="test-mosque",
            timezone="Europe/Paris",
        )

        self.user = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="TestPass123!",
            mosque=self.mosque,
            role="ADMIN",
        )

        self.login_url = reverse("core:login")
        self.refresh_url = reverse("core:token_refresh")
        self.logout_url = reverse("core:logout")

    # -- Login -----------------------------------------------------------------

    def test_login_success(self) -> None:
        """Login avec credentials valides -> 200 + access + refresh."""
        response = self.client.post(
            self.login_url,
            {"username": "admin_test", "password": "TestPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)

    def test_login_invalid_credentials(self) -> None:
        """Login avec mauvais mot de passe -> 401."""
        response = self.client.post(
            self.login_url,
            {"username": "admin_test", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self) -> None:
        """Login sans champs requis -> 400."""
        response = self.client.post(self.login_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Refresh ---------------------------------------------------------------

    def test_refresh_token(self) -> None:
        """Refresh token valide -> 200 + nouvel access token."""
        login_response = self.client.post(
            self.login_url,
            {"username": "admin_test", "password": "TestPass123!"},
            format="json",
        )
        refresh_token = login_response.json()["refresh"]

        response = self.client.post(
            self.refresh_url,
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.json())

    # -- Logout ----------------------------------------------------------------

    def test_logout_success(self) -> None:
        """Logout avec refresh token valide -> 204."""
        login_response = self.client.post(
            self.login_url,
            {"username": "admin_test", "password": "TestPass123!"},
            format="json",
        )
        tokens = login_response.json()
        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.post(
            self.logout_url,
            {"refresh": refresh_token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logout_without_token(self) -> None:
        """Logout sans champ refresh -> 400."""
        login_response = self.client.post(
            self.login_url,
            {"username": "admin_test", "password": "TestPass123!"},
            format="json",
        )
        access_token = login_response.json()["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.post(self.logout_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self) -> None:
        """Logout sans etre authentifie -> 401."""
        response = self.client.post(
            self.logout_url,
            {"refresh": "fake_token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -- Permissions RBAC ------------------------------------------------------

    def test_has_mosque_permission_grants_access(self) -> None:
        """HasMosquePermission : user avec mosquee -> True + request.mosque injecte."""
        from rest_framework.request import Request as DrfReq
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken as RT

        factory = APIRequestFactory()
        raw_request = factory.get("/api/test/")

        refresh = RT.for_user(self.user)
        access_token = str(refresh.access_token)

        auth = JWTAuthentication()
        drf_req = DrfReq(raw_request, authenticators=[auth])
        validated_token = auth.get_validated_token(access_token)
        user = auth.get_user(validated_token)
        drf_req._user = user
        drf_req._auth = validated_token

        perm = HasMosquePermission()
        result = perm.has_permission(drf_req, None)
        self.assertTrue(result)
        self.assertEqual(drf_req.mosque, self.mosque)

    def test_has_mosque_permission_blocks_user_without_mosque(self) -> None:
        """HasMosquePermission : user sans mosquee -> False."""
        from rest_framework.request import Request as DrfReq
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import RefreshToken as RT

        orphan = User.objects.create_user(
            username="orphan",
            email="orphan@test.com",
            password="TestPass123!",
        )

        factory = APIRequestFactory()
        raw_request = factory.get("/api/test/")

        refresh = RT.for_user(orphan)
        access_token = str(refresh.access_token)

        auth = JWTAuthentication()
        drf_req = DrfReq(raw_request, authenticators=[auth])
        validated_token = auth.get_validated_token(access_token)
        user = auth.get_user(validated_token)
        drf_req._user = user
        drf_req._auth = validated_token

        perm = HasMosquePermission()
        result = perm.has_permission(drf_req, None)
        self.assertFalse(result)
