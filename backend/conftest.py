"""
conftest.py — Fixtures pytest partagées entre toutes les apps
==============================================================
Disponible dans tous les fichiers tests.py sans import.

Fixtures disponibles :
    mosque          → instance Mosque
    mosque_b        → deuxième mosquée (isolation cross-tenant)
    admin_user      → User ADMIN lié à mosque
    ecole_user      → User ECOLE_MANAGER lié à mosque
    tresorier_user  → User TRESORIER lié à mosque
    other_user      → User ADMIN lié à mosque_b (cross-tenant)
    api_client      → APIClient non authentifié
    admin_client    → APIClient authentifié en ADMIN
    ecole_client    → APIClient authentifié en ECOLE_MANAGER
    tresorier_client→ APIClient authentifié en TRESORIER
    school_year     → SchoolYear actif lié à mosque
    membership_year → MembershipYear lié à mosque
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from core.models import Mosque, MosqueSettings, User
from school.models import SchoolYear
from membership.models import MembershipYear


# ── Mosquées ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mosque(db):
    m = Mosque.objects.create(name="Mosquée Test", slug="test", timezone="Europe/Paris")
    # Le signal crée déjà MosqueSettings — on met à jour avec les valeurs de test
    MosqueSettings.objects.update_or_create(
        mosque=m,
        defaults={
            "active_school_year_label": "2025-2026",
            "school_fee_default": 500,
            "school_fee_mode": "annual",
            "school_levels": ["NP", "N1", "N2", "N3"],
            "membership_fee_amount": 50,
            "membership_fee_mode": "per_person",
        },
    )
    return m


@pytest.fixture
def mosque_b(db):
    """Deuxième mosquée — pour tester l'isolation multi-tenant."""
    m = Mosque.objects.create(name="Autre Mosquée", slug="autre", timezone="Europe/Paris")
    MosqueSettings.objects.update_or_create(
        mosque=m,
        defaults={
            "active_school_year_label": "2025-2026",
            "school_fee_default": 500,
            "membership_fee_amount": 50,
        },
    )
    return m


# ── Utilisateurs ──────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(mosque):
    return User.objects.create_user(
        username="admin_test", email="admin@test.com",
        password="AdminPass123!", mosque=mosque, role="ADMIN",
    )


@pytest.fixture
def ecole_user(mosque):
    return User.objects.create_user(
        username="ecole_test", email="ecole@test.com",
        password="EcolePass123!", mosque=mosque, role="ECOLE_MANAGER",
    )


@pytest.fixture
def tresorier_user(mosque):
    return User.objects.create_user(
        username="tresorier_test", email="tresorier@test.com",
        password="TresoPass123!", mosque=mosque, role="TRESORIER",
    )


@pytest.fixture
def other_user(mosque_b):
    """User d'une autre mosquée — ne doit jamais voir les données de mosque."""
    return User.objects.create_user(
        username="other_test", email="other@test.com",
        password="OtherPass123!", mosque=mosque_b, role="ADMIN",
    )


# ── Clients API ───────────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


def _authenticated_client(user):
    """Helper interne : crée un APIClient avec token JWT."""
    client = APIClient()
    response = client.post(
        reverse("core:login"),
        {"username": user.username, "password": _get_raw_password(user)},
        format="json",
    )
    assert response.status_code == 200, f"Login échoué pour {user.username}: {response.data}"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


# Mapping username → password en clair (cohérent avec les fixtures ci-dessus)
_PASSWORDS = {
    "admin_test":     "AdminPass123!",
    "ecole_test":     "EcolePass123!",
    "tresorier_test": "TresoPass123!",
    "other_test":     "OtherPass123!",
}

def _get_raw_password(user):
    return _PASSWORDS.get(user.username, "TestPass123!")


@pytest.fixture
def admin_client(admin_user):
    return _authenticated_client(admin_user)


@pytest.fixture
def ecole_client(ecole_user):
    return _authenticated_client(ecole_user)


@pytest.fixture
def tresorier_client(tresorier_user):
    return _authenticated_client(tresorier_user)


@pytest.fixture
def other_client(other_user):
    return _authenticated_client(other_user)


# ── Données de base ───────────────────────────────────────────────────────────

@pytest.fixture
def school_year(mosque):
    # Le signal a peut-être déjà créé une SchoolYear "2025-2026" — on update
    sy, _ = SchoolYear.objects.update_or_create(
        mosque=mosque, label="2025-2026",
        defaults={"start_date": "2025-09-01", "end_date": "2026-06-30", "is_active": True},
    )
    return sy


@pytest.fixture
def membership_year(mosque):
    my, _ = MembershipYear.objects.update_or_create(
        mosque=mosque, year=2026,
        defaults={"amount_expected": 50, "is_active": True},
    )
    return my
