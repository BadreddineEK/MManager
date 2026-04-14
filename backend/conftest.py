"""
conftest.py — Fixtures pytest partagées (multi-tenant)
=======================================================
Adapte django-tenants : chaque fixture mosque cree un vrai schema PostgreSQL.
"""
import pytest
from django.db import connection
from django.urls import reverse
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context

from core.models import Domain, Mosque, MosqueSettings, User
from school.models import SchoolYear
from membership.models import MembershipYear


def _create_mosque(schema_name, name, slug, settings_defaults):
    """Cree un tenant Mosque + Domain dans le schema public."""
    connection.set_schema_to_public()
    m = Mosque(schema_name=schema_name, name=name, slug=slug, timezone="Europe/Paris")
    m.save()
    Domain.objects.get_or_create(
        tenant=m,
        domain=f"{schema_name}.test.nidham.local",
        defaults={"is_primary": True},
    )
    with schema_context(schema_name):
        MosqueSettings.objects.update_or_create(
            mosque=m,
            defaults=settings_defaults,
        )
    return m


@pytest.fixture(scope="function")
def mosque(db):
    return _create_mosque(
        schema_name="testmosque",
        name="Mosquee Test",
        slug="test",
        settings_defaults={
            "active_school_year_label": "2025-2026",
            "school_fee_default": 500,
            "school_fee_mode": "annual",
            "school_levels": ["NP", "N1", "N2", "N3"],
            "membership_fee_amount": 50,
            "membership_fee_mode": "per_person",
        },
    )


@pytest.fixture(scope="function")
def mosque_b(db):
    return _create_mosque(
        schema_name="testmosque2",
        name="Autre Mosquee",
        slug="autre",
        settings_defaults={
            "active_school_year_label": "2025-2026",
            "school_fee_default": 500,
            "membership_fee_amount": 50,
        },
    )


@pytest.fixture
def admin_user(mosque):
    with schema_context(mosque.schema_name):
        return User.objects.create_user(
            username="admin_test", email="admin@test.com",
            password="AdminPass123!", mosque=mosque, role="ADMIN",
        )


@pytest.fixture
def ecole_user(mosque):
    with schema_context(mosque.schema_name):
        return User.objects.create_user(
            username="ecole_test", email="ecole@test.com",
            password="EcolePass123!", mosque=mosque, role="ECOLE_MANAGER",
        )


@pytest.fixture
def tresorier_user(mosque):
    with schema_context(mosque.schema_name):
        return User.objects.create_user(
            username="tresorier_test", email="tresorier@test.com",
            password="TresoPass123!", mosque=mosque, role="TRESORIER",
        )


@pytest.fixture
def other_user(mosque_b):
    with schema_context(mosque_b.schema_name):
        return User.objects.create_user(
            username="other_test", email="other@test.com",
            password="OtherPass123!", mosque=mosque_b, role="ADMIN",
        )


@pytest.fixture
def api_client(mosque):
    return TenantClient(mosque)


def _authenticated_client(mosque, user, password):
    connection.set_schema_to_public()
    client = TenantClient(mosque)
    response = client.post(
        reverse("core:login"),
        {"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 200, f"Login echoue pour {user.username}: {response.data}"
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {response.data['access']}"
    return client


@pytest.fixture
def admin_client(mosque, admin_user):
    return _authenticated_client(mosque, admin_user, "AdminPass123!")


@pytest.fixture
def ecole_client(mosque, ecole_user):
    return _authenticated_client(mosque, ecole_user, "EcolePass123!")


@pytest.fixture
def tresorier_client(mosque, tresorier_user):
    return _authenticated_client(mosque, tresorier_user, "TresoPass123!")


@pytest.fixture
def other_client(mosque_b, other_user):
    return _authenticated_client(mosque_b, other_user, "OtherPass123!")


@pytest.fixture
def school_year(mosque):
    with schema_context(mosque.schema_name):
        sy, _ = SchoolYear.objects.update_or_create(
            mosque=mosque, label="2025-2026",
            defaults={"start_date": "2025-09-01", "end_date": "2026-06-30", "is_active": True},
        )
    return sy


@pytest.fixture
def membership_year(mosque):
    with schema_context(mosque.schema_name):
        my, _ = MembershipYear.objects.update_or_create(
            mosque=mosque, year=2026,
            defaults={"amount_expected": 50, "is_active": True},
        )
    return my
