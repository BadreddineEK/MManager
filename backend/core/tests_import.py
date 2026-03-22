"""
Tests import en masse — CSV
============================
Couverture :
  ImportTransactionsView
    - Dry run : rapport sans écriture en base
    - Import réel : transactions créées
    - Fichier vide : 0 importé
    - Lignes invalides (montants manquants, dates malformées) → skipped/errors
    - Accès refusé sans auth → 401
    - Accès refusé si non-ADMIN → 403

  ImportMembersView
    - Dry run : rapport would_create
    - Import réel : membres + paiements créés
    - Paiement mensuel détaillé (jan..dec)
    - Fallback total_paye si pas de mois

  ImportSchoolView
    - Dry run : rapport would_create
    - Import réel : familles + enfants + paiements
    - Paiement par mois scolaire (sept..juin)
    - Fallback total_verse
"""
import csv
import io

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

# ─ pytest-django ─
import pytest

from core.models import Mosque, User
from membership.models import Member, MembershipPayment, MembershipYear
from school.models import Child, Family, SchoolPayment, SchoolYear
from treasury.models import TreasuryTransaction


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture
def mosque(db):
    return Mosque.objects.create(name="Import Mosque", slug="import-mosque")


@pytest.fixture
def admin_user(mosque):
    return User.objects.create_user(
        username="import_admin",
        password="Pass123!",
        mosque=mosque,
        role="ADMIN",
    )


@pytest.fixture
def ecole_user(mosque):
    return User.objects.create_user(
        username="import_ecole",
        password="Pass123!",
        mosque=mosque,
        role="ECOLE_MANAGER",
    )


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def ecole_client(ecole_user):
    client = APIClient()
    client.force_authenticate(user=ecole_user)
    return client


@pytest.fixture
def membership_year(mosque):
    return MembershipYear.objects.create(
        mosque=mosque, year=2025, amount_expected=120, is_active=True
    )


@pytest.fixture
def school_year(mosque):
    from datetime import date
    sy, _ = SchoolYear.objects.update_or_create(
        mosque=mosque,
        label="2025-2026",
        defaults={
            "start_date": date(2025, 9, 1),
            "end_date":   date(2026, 6, 30),
            "is_active":  True,
        },
    )
    return sy


def _make_csv(rows: list[dict]) -> io.BytesIO:
    """Génère un fichier CSV en mémoire depuis une liste de dicts."""
    if not rows:
        return io.BytesIO(b"date,objet,montant_entree,montant_sortie,categorie\n")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return io.BytesIO(buf.getvalue().encode("utf-8"))


# ─────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────

TX_URL = "/api/import/transactions/"


@pytest.mark.django_db
class TestImportTransactions:

    def test_dry_run_does_not_create(self, admin_client, mosque):
        csv_file = _make_csv([
            {"date": "01/09/2025", "objet": "Don test", "montant_entree": "100", "montant_sortie": "", "categorie": "don"},
            {"date": "02/09/2025", "objet": "Loyer", "montant_entree": "", "montant_sortie": "500", "categorie": "loyer"},
        ])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {
            "file": csv_file,
            "mosque_id": mosque.id,
            "dry_run": "true",
        }, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["dry_run"] is True
        assert data["would_create"] == 2
        assert TreasuryTransaction.objects.filter(mosque=mosque).count() == 0

    def test_real_import_creates_transactions(self, admin_client, mosque):
        csv_file = _make_csv([
            {"date": "01/09/2025", "objet": "Don", "montant_entree": "200", "montant_sortie": "", "categorie": "don"},
            {"date": "05/09/2025", "objet": "EDF", "montant_entree": "", "montant_sortie": "98.50", "categorie": "facture"},
            {"date": "10/09/2025", "objet": "Cotisation", "montant_entree": "50", "montant_sortie": "", "categorie": "cotisation"},
        ])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {
            "file": csv_file,
            "mosque_id": mosque.id,
            "dry_run": "false",
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.json()["imported"] == 3
        assert TreasuryTransaction.objects.filter(mosque=mosque).count() == 3

    def test_direction_in_out_detected(self, admin_client, mosque):
        csv_file = _make_csv([
            {"date": "01/01/2025", "objet": "Recette", "montant_entree": "300", "montant_sortie": "", "categorie": "don"},
            {"date": "02/01/2025", "objet": "Depense", "montant_entree": "", "montant_sortie": "150", "categorie": "loyer"},
        ])
        csv_file.name = "tx.csv"
        admin_client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "false"}, format="multipart")
        txs = TreasuryTransaction.objects.filter(mosque=mosque).order_by("date")
        assert txs[0].direction == "IN"
        assert txs[0].amount == 300
        assert txs[1].direction == "OUT"
        assert txs[1].amount == 150

    def test_skips_rows_without_amount(self, admin_client, mosque):
        csv_file = _make_csv([
            {"date": "01/01/2025", "objet": "Vide", "montant_entree": "", "montant_sortie": "", "categorie": "don"},
            {"date": "02/01/2025", "objet": "Réel", "montant_entree": "50", "montant_sortie": "", "categorie": "don"},
        ])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "false"}, format="multipart")
        assert resp.json()["imported"] == 1
        assert resp.json()["skipped"] == 1

    def test_invalid_date_is_skipped(self, admin_client, mosque):
        csv_file = _make_csv([
            {"date": "not-a-date", "objet": "X", "montant_entree": "10", "montant_sortie": "", "categorie": "don"},
            {"date": "01/01/2025", "objet": "OK", "montant_entree": "10", "montant_sortie": "", "categorie": "don"},
        ])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "false"}, format="multipart")
        assert resp.json()["imported"] == 1

    def test_category_mapping(self, admin_client, mosque):
        csv_file = _make_csv([
            {"date": "01/01/2025", "objet": "Test", "montant_entree": "10", "montant_sortie": "", "categorie": "Cotisation Mosquée"},
        ])
        csv_file.name = "tx.csv"
        admin_client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "false"}, format="multipart")
        tx = TreasuryTransaction.objects.filter(mosque=mosque).first()
        assert tx.category == "cotisation"

    def test_unauthenticated_rejected(self, mosque):
        client = APIClient()
        csv_file = _make_csv([{"date": "01/01/2025", "objet": "X", "montant_entree": "10", "montant_sortie": "", "categorie": "don"}])
        csv_file.name = "tx.csv"
        resp = client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "true"}, format="multipart")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_admin_rejected(self, ecole_client, mosque):
        csv_file = _make_csv([{"date": "01/01/2025", "objet": "X", "montant_entree": "10", "montant_sortie": "", "categorie": "don"}])
        csv_file.name = "tx.csv"
        resp = ecole_client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "true"}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_wrong_mosque_rejected(self, admin_client):
        other = Mosque.objects.create(name="Autre", slug="autre")
        csv_file = _make_csv([{"date": "01/01/2025", "objet": "X", "montant_entree": "10", "montant_sortie": "", "categorie": "don"}])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {"file": csv_file, "mosque_id": other.id, "dry_run": "true"}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_missing_mosque_id(self, admin_client):
        csv_file = _make_csv([])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {"file": csv_file}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_file(self, admin_client, mosque):
        resp = admin_client.post(TX_URL, {"mosque_id": mosque.id, "dry_run": "true"}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_annee_mois_fallback(self, admin_client, mosque):
        """Si 'date' est vide, reconstruit depuis annee + mois."""
        csv_file = _make_csv([
            {"date": "", "annee": "2025", "mois": "3", "objet": "Virement", "montant_entree": "100", "montant_sortie": "", "categorie": "don"},
        ])
        csv_file.name = "tx.csv"
        resp = admin_client.post(TX_URL, {"file": csv_file, "mosque_id": mosque.id, "dry_run": "false"}, format="multipart")
        assert resp.json()["imported"] == 1
        tx = TreasuryTransaction.objects.filter(mosque=mosque).first()
        assert tx.date.year == 2025
        assert tx.date.month == 3

    def test_isolation_between_mosques(self, admin_client, mosque):
        other = Mosque.objects.create(name="Autre Mosquée", slug="autre-mosquee")
        # Insérer une transaction dans l'autre mosquée directement
        from datetime import date
        TreasuryTransaction.objects.create(
            mosque=other, date=date(2025, 1, 1),
            label="Autre", direction="IN", amount=100, category="don"
        )
        assert TreasuryTransaction.objects.filter(mosque=mosque).count() == 0


# ─────────────────────────────────────────────────────────────────
# Membres
# ─────────────────────────────────────────────────────────────────

MEMBERS_URL = "/api/import/members/"


def _members_csv(rows):
    csv_file = _make_csv(rows)
    csv_file.name = "members.csv"
    return csv_file


@pytest.mark.django_db
class TestImportMembers:

    def test_dry_run(self, admin_client, mosque, membership_year):
        f = _members_csv([
            {"nom_prenom": "MARTIN Pierre", "telephone": "0612345678", "email": "", "adresse": "",
             "mode_paiement": "virement", "total_paye": "120",
             "jan": "10", "fev": "10", "mars": "10", "avr": "10", "mai": "10", "juin": "10",
             "juil": "", "aout": "", "sept": "10", "oct": "10", "nov": "10", "dec": "10"},
        ])
        resp = admin_client.post(MEMBERS_URL, {
            "file": f, "mosque_id": mosque.id,
            "membership_year": membership_year.id, "dry_run": "true",
        }, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["dry_run"] is True
        assert data["would_create"]["members"] == 1
        assert data["would_create"]["payments"] == 10  # jan..juin + sept..dec = 10 mois avec montant
        assert Member.objects.filter(mosque=mosque).count() == 0

    def test_real_import_creates_member_and_payments(self, admin_client, mosque, membership_year):
        f = _members_csv([
            {"nom_prenom": "DUPONT Ahmed", "telephone": "0698765432", "email": "ahmed@test.com",
             "adresse": "5 rue Test", "mode_paiement": "cheque", "total_paye": "40",
             "jan": "", "fev": "", "mars": "", "avr": "", "mai": "", "juin": "",
             "juil": "", "aout": "", "sept": "10", "oct": "10", "nov": "10", "dec": "10"},
        ])
        resp = admin_client.post(MEMBERS_URL, {
            "file": f, "mosque_id": mosque.id,
            "membership_year": membership_year.id, "dry_run": "false",
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Member.objects.filter(mosque=mosque, full_name="DUPONT Ahmed").exists()
        assert MembershipPayment.objects.filter(mosque=mosque).count() == 4

    def test_fallback_total_paye(self, admin_client, mosque, membership_year):
        """Si aucun mois renseigné → un seul paiement avec total_paye."""
        f = _members_csv([
            {"nom_prenom": "BEN ALI Youssef", "telephone": "", "email": "", "adresse": "",
             "mode_paiement": "especes", "total_paye": "80",
             "jan": "", "fev": "", "mars": "", "avr": "", "mai": "", "juin": "",
             "juil": "", "aout": "", "sept": "", "oct": "", "nov": "", "dec": ""},
        ])
        resp = admin_client.post(MEMBERS_URL, {
            "file": f, "mosque_id": mosque.id,
            "membership_year": membership_year.id, "dry_run": "false",
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED
        assert MembershipPayment.objects.filter(mosque=mosque).count() == 1
        p = MembershipPayment.objects.filter(mosque=mosque).first()
        assert p.amount == 80

    def test_no_duplicate_member(self, admin_client, mosque, membership_year):
        """Membre déjà en base → pas re-créé."""
        Member.objects.create(mosque=mosque, full_name="EXISTANT Marie", phone="")
        f = _members_csv([
            {"nom_prenom": "EXISTANT Marie", "telephone": "", "email": "", "adresse": "",
             "mode_paiement": "", "total_paye": "50",
             "jan": "", "fev": "", "mars": "", "avr": "", "mai": "50", "juin": "",
             "juil": "", "aout": "", "sept": "", "oct": "", "nov": "", "dec": ""},
        ])
        admin_client.post(MEMBERS_URL, {
            "file": f, "mosque_id": mosque.id,
            "membership_year": membership_year.id, "dry_run": "false",
        }, format="multipart")
        assert Member.objects.filter(mosque=mosque, full_name="EXISTANT Marie").count() == 1

    def test_missing_year_rejected(self, admin_client, mosque):
        f = _members_csv([{"nom_prenom": "X"}])
        resp = admin_client.post(MEMBERS_URL, {
            "file": f, "mosque_id": mosque.id,
        }, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─────────────────────────────────────────────────────────────────
# École
# ─────────────────────────────────────────────────────────────────

SCHOOL_URL = "/api/import/school/"


def _school_csv(rows):
    csv_file = _make_csv(rows)
    csv_file.name = "ecole.csv"
    return csv_file


@pytest.mark.django_db
class TestImportSchool:

    def test_dry_run(self, admin_client, mosque, school_year):
        f = _school_csv([
            {"nom_parents": "MARTIN Pierre", "prenom_enfant": "Yasmine", "niveau": "N2",
             "total_du": "180", "total_verse": "180",
             "sept": "20", "oct": "20", "nov": "20", "dec": "20",
             "jan": "20", "fev": "20", "mars": "20", "avr": "20", "mai": "20", "juin": "20",
             "tel_papa": "0612345678", "tel_maman": "", "email": ""},
        ])
        resp = admin_client.post(SCHOOL_URL, {
            "file": f, "mosque_id": mosque.id,
            "school_year": school_year.id, "dry_run": "true",
        }, format="multipart")
        assert resp.status_code == status.HTTP_200_OK
        d = resp.json()
        assert d["dry_run"] is True
        assert d["would_create"]["families"] == 1
        assert d["would_create"]["children"] == 1
        assert d["would_create"]["payments"] == 10
        assert Family.objects.filter(mosque=mosque).count() == 0

    def test_real_import(self, admin_client, mosque, school_year):
        f = _school_csv([
            {"nom_parents": "DUPONT Ahmed", "prenom_enfant": "Omar", "niveau": "N1",
             "total_du": "80", "total_verse": "60",
             "sept": "", "oct": "", "nov": "20", "dec": "20",
             "jan": "20", "fev": "", "mars": "", "avr": "", "mai": "", "juin": "",
             "tel_papa": "0698765432", "tel_maman": "", "email": ""},
        ])
        resp = admin_client.post(SCHOOL_URL, {
            "file": f, "mosque_id": mosque.id,
            "school_year": school_year.id, "dry_run": "false",
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Family.objects.filter(mosque=mosque).exists()
        assert Child.objects.filter(mosque=mosque, first_name="Omar").exists()
        assert SchoolPayment.objects.filter(mosque=mosque).count() == 3

    def test_fallback_total_verse(self, admin_client, mosque, school_year):
        f = _school_csv([
            {"nom_parents": "BENALI Fatima", "prenom_enfant": "Sara", "niveau": "NP",
             "total_du": "120", "total_verse": "60",
             "sept": "", "oct": "", "nov": "", "dec": "",
             "jan": "", "fev": "", "mars": "", "avr": "", "mai": "", "juin": "",
             "tel_papa": "", "tel_maman": "0644443333", "email": ""},
        ])
        resp = admin_client.post(SCHOOL_URL, {
            "file": f, "mosque_id": mosque.id,
            "school_year": school_year.id, "dry_run": "false",
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED
        assert SchoolPayment.objects.filter(mosque=mosque).count() == 1
        p = SchoolPayment.objects.filter(mosque=mosque).first()
        assert p.amount == 60

    def test_no_duplicate_family(self, admin_client, mosque, school_year):
        Family.objects.create(mosque=mosque, primary_contact_name="EXISTANT Paul", phone1="")
        f = _school_csv([
            {"nom_parents": "EXISTANT Paul", "prenom_enfant": "Lea", "niveau": "N3",
             "total_du": "60", "total_verse": "60",
             "sept": "60", "oct": "", "nov": "", "dec": "",
             "jan": "", "fev": "", "mars": "", "avr": "", "mai": "", "juin": "",
             "tel_papa": "", "tel_maman": "", "email": ""},
        ])
        admin_client.post(SCHOOL_URL, {
            "file": f, "mosque_id": mosque.id,
            "school_year": school_year.id, "dry_run": "false",
        }, format="multipart")
        assert Family.objects.filter(mosque=mosque, primary_contact_name="EXISTANT Paul").count() == 1

    def test_empty_nom_parents_skipped(self, admin_client, mosque, school_year):
        f = _school_csv([
            {"nom_parents": "", "prenom_enfant": "Orphan", "niveau": "N1",
             "total_du": "50", "total_verse": "50",
             "sept": "50", "oct": "", "nov": "", "dec": "",
             "jan": "", "fev": "", "mars": "", "avr": "", "mai": "", "juin": "",
             "tel_papa": "", "tel_maman": "", "email": ""},
        ])
        resp = admin_client.post(SCHOOL_URL, {
            "file": f, "mosque_id": mosque.id,
            "school_year": school_year.id, "dry_run": "false",
        }, format="multipart")
        assert resp.json()["skipped"] == 1
        assert Family.objects.filter(mosque=mosque).count() == 0

    def test_missing_school_year_rejected(self, admin_client, mosque):
        f = _school_csv([{"nom_parents": "X"}])
        resp = admin_client.post(SCHOOL_URL, {
            "file": f, "mosque_id": mosque.id,
        }, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
