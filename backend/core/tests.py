"""
Tests core — Auth JWT + RBAC + Audit Log + Users
=================================================
Couverture :
  Auth
    - Login valide → 200 + tokens
    - Login invalide → 401
    - Login champs manquants → 400
    - Refresh token → 200
    - Logout → 204 / sans refresh → 400 / non auth → 401

  RBAC (HasMosquePermission)
    - user avec mosquée → True + request.mosque injecté
    - user sans mosquée → False

  Audit Log
    - GET /api/audit/ accessible à l'ADMIN
    - GET /api/audit/ refusé au non-ADMIN
    - Une action CREATE génère bien une entrée d'audit
    - Les filtres ?action=, ?entity= fonctionnent

  Users
    - ADMIN peut lister / créer / modifier / supprimer
    - ADMIN ne peut pas se supprimer lui-même
    - non-ADMIN ne peut pas accéder à /api/users/
    - GET /api/users/me/ accessible à tout rôle
"""
from django.test import TestCase
from django_tenants.test.cases import TenantTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django_tenants.test.client import TenantClient

from .models import AuditLog, Mosque, User
from .permissions import HasMosquePermission


class AuthTestCase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls): return "authtest1"
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "Auth Test 1"
        tenant.slug = "authtest1"
    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        schema = cls.tenant.schema_name
        mosque_id = cls.tenant.pk
        connection.set_schema_to_public()
        # Drop du schema tenant (tables school_year, etc.)
        with connection.cursor() as c:
            c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        # Supprimer domaine et FK dependants (ordre important)
        with connection.cursor() as c:
            c.execute("DELETE FROM core_domain WHERE tenant_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosquesettings WHERE mosque_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosque WHERE id = %s", [mosque_id])
        cls.remove_allowed_test_domain()
    """Tests du flux d'authentification JWT."""

    def setUp(self) -> None:
        self.mosque = self.tenant  # TenantTestCase
        self.client = TenantClient(self.tenant)  # TenantTestCase fournit self.tenant

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

        self.client.defaults.__setitem__("HTTP_AUTHORIZATION",f"Bearer {access_token}")
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

        self.client.defaults.__setitem__("HTTP_AUTHORIZATION",f"Bearer {access_token}")
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


class AuditLogTestCase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls): return "auditlog"
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "Audit Log Test"
        tenant.slug = "auditlog"
    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        schema = cls.tenant.schema_name
        mosque_id = cls.tenant.pk
        connection.set_schema_to_public()
        # Drop du schema tenant (tables school_year, etc.)
        with connection.cursor() as c:
            c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        # Supprimer domaine et FK dependants (ordre important)
        with connection.cursor() as c:
            c.execute("DELETE FROM core_domain WHERE tenant_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosquesettings WHERE mosque_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosque WHERE id = %s", [mosque_id])
        cls.remove_allowed_test_domain()
    """Tests du journal d'audit."""

    def setUp(self):
        self.client = TenantClient(self.tenant)
        self.mosque = self.tenant  # TenantTestCase fournit self.tenant
        self.admin = User.objects.create_user(
            username="audit_admin", email="audit@test.com",
            password="AuditPass123!", mosque=self.mosque, role="ADMIN",
        )
        self.ecole = User.objects.create_user(
            username="audit_ecole", email="ecole@test.com",
            password="EcolePass123!", mosque=self.mosque, role="ECOLE_MANAGER",
        )
        self.login_url = reverse("core:login")
        self.audit_url = "/api/audit/"

    def _login(self, username, password):
        res = self.client.post(self.login_url, {"username": username, "password": password}, format="json")
        self.client.defaults.__setitem__("HTTP_AUTHORIZATION",f"Bearer {res.data['access']}")

    def test_admin_can_access_audit_log(self):
        self._login("audit_admin", "AuditPass123!")
        res = self.client.get(self.audit_url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data)

    def test_non_admin_cannot_access_audit_log(self):
        """ECOLE_MANAGER ne peut pas lire le journal d'audit."""
        self._login("audit_ecole", "EcolePass123!")
        res = self.client.get(self.audit_url)
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_cannot_access_audit_log(self):
        self.client.defaults.pop("HTTP_AUTHORIZATION", None)
        res = self.client.get(self.audit_url)
        self.assertEqual(res.status_code, 401)

    def test_audit_entry_created_on_action(self):
        """Une écriture dans une vue logguée génère bien une entrée AuditLog."""
        from core.utils import log_action

        class FakeRequest:
            user = self.admin
            mosque = self.mosque

        initial_count = AuditLog.objects.filter(mosque=self.mosque).count()
        log_action(FakeRequest(), "CREATE", "TestEntity", 42, {"test": "value"})
        self.assertEqual(AuditLog.objects.filter(mosque=self.mosque).count(), initial_count + 1)

    def test_audit_filter_by_action(self):
        """Le filtre ?action= retourne uniquement les entrées correspondantes."""
        AuditLog.objects.create(mosque=self.mosque, user=self.admin, action="CREATE", entity="Family", entity_id=1, payload={})
        AuditLog.objects.create(mosque=self.mosque, user=self.admin, action="DELETE", entity="Family", entity_id=1, payload={})
        AuditLog.objects.create(mosque=self.mosque, user=self.admin, action="CREATE", entity="Member", entity_id=2, payload={})

        self._login("audit_admin", "AuditPass123!")
        res = self.client.get(f"{self.audit_url}?action=CREATE")
        self.assertEqual(res.status_code, 200)
        actions = [e["action"] for e in res.data["results"]]
        self.assertTrue(all(a == "CREATE" for a in actions))
        self.assertEqual(len(actions), 2)

    def test_audit_filter_by_entity(self):
        AuditLog.objects.create(mosque=self.mosque, user=self.admin, action="CREATE", entity="Family", entity_id=1, payload={})
        AuditLog.objects.create(mosque=self.mosque, user=self.admin, action="CREATE", entity="Member", entity_id=2, payload={})

        self._login("audit_admin", "AuditPass123!")
        res = self.client.get(f"{self.audit_url}?entity=Family")
        self.assertEqual(res.status_code, 200)
        entities = [e["entity"] for e in res.data["results"]]
        self.assertTrue(all(e == "Family" for e in entities))


class UserManagementTestCase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls): return "usermgmt"
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "User Mgmt Test"
        tenant.slug = "usermgmt"
    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        schema = cls.tenant.schema_name
        mosque_id = cls.tenant.pk
        connection.set_schema_to_public()
        # Drop du schema tenant (tables school_year, etc.)
        with connection.cursor() as c:
            c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        # Supprimer domaine et FK dependants (ordre important)
        with connection.cursor() as c:
            c.execute("DELETE FROM core_domain WHERE tenant_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosquesettings WHERE mosque_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosque WHERE id = %s", [mosque_id])
        cls.remove_allowed_test_domain()
    """Tests de la gestion des utilisateurs."""

    def setUp(self):
        self.client = TenantClient(self.tenant)
        self.mosque = self.tenant  # TenantTestCase fournit self.tenant
        self.admin = User.objects.create_user(
            username="admin_users", email="admin@users.com",
            password="AdminPass123!", mosque=self.mosque, role="ADMIN",
        )
        self.ecole = User.objects.create_user(
            username="ecole_users", email="ecole@users.com",
            password="EcolePass123!", mosque=self.mosque, role="ECOLE_MANAGER",
        )
        self.login_url = reverse("core:login")
        self.users_url = "/api/users/"
        self.me_url = "/api/users/me/"

    def _login(self, username, password):
        res = self.client.post(self.login_url, {"username": username, "password": password}, format="json")
        self.client.defaults.__setitem__("HTTP_AUTHORIZATION",f"Bearer {res.data['access']}")

    def test_admin_can_list_users(self):
        self._login("admin_users", "AdminPass123!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, 200)

    def test_non_admin_cannot_list_users(self):
        self._login("ecole_users", "EcolePass123!")
        res = self.client.get(self.users_url)
        self.assertEqual(res.status_code, 403)

    def test_admin_can_create_user(self):
        self._login("admin_users", "AdminPass123!")
        res = self.client.post(self.users_url, {
            "username": "nouveau_user",
            "email": "nouveau@test.com",
            "password": "NouveauPass123!",
            "role": "TRESORIER",
        }, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["role"], "TRESORIER")

    def test_admin_cannot_delete_himself(self):
        self._login("admin_users", "AdminPass123!")
        res = self.client.delete(f"{self.users_url}{self.admin.id}/")
        self.assertEqual(res.status_code, 400)

    def test_me_endpoint_returns_current_user(self):
        self._login("ecole_users", "EcolePass123!")
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["username"], "ecole_users")

    def test_me_endpoint_unauthenticated(self):
        self.client.defaults.pop("HTTP_AUTHORIZATION", None)
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, 401)


class AuthTestCase(TenantTestCase):
    @classmethod
    def get_test_schema_name(cls): return "authtest2"
    @classmethod
    def setup_tenant(cls, tenant):
        tenant.name = "Auth Test 2"
        tenant.slug = "authtest2"
    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        schema = cls.tenant.schema_name
        mosque_id = cls.tenant.pk
        connection.set_schema_to_public()
        # Drop du schema tenant (tables school_year, etc.)
        with connection.cursor() as c:
            c.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        # Supprimer domaine et FK dependants (ordre important)
        with connection.cursor() as c:
            c.execute("DELETE FROM core_domain WHERE tenant_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosquesettings WHERE mosque_id = %s", [mosque_id])
            c.execute("DELETE FROM core_mosque WHERE id = %s", [mosque_id])
        cls.remove_allowed_test_domain()
    """Tests du flux d'authentification JWT."""

    def setUp(self) -> None:
        self.mosque = self.tenant  # TenantTestCase
        self.client = TenantClient(self.tenant)  # TenantTestCase fournit self.tenant

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

        self.client.defaults.__setitem__("HTTP_AUTHORIZATION",f"Bearer {access_token}")
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

        self.client.defaults.__setitem__("HTTP_AUTHORIZATION",f"Bearer {access_token}")
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
