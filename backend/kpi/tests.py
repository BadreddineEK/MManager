"""
Tests KPI
=========
Couverture :
  GET /api/kpi/summary/?mosque=<slug>
    - sans param mosque → 400
    - slug inconnu → 404
    - accessible sans authentification (AllowAny)
    - retourne les clés attendues (school / membership / treasury / campaigns)
    - aucun PII dans la réponse (pas de noms, emails, téléphones)
    - agrégats cohérents : children, membres, entrées/sorties
    - filtre par mois via ?month=YYYY-MM

  GET /api/kpi/mosques/
    - retourne la liste des mosquées (slug + name) sans auth
"""
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import Mosque, MosqueSettings, User
from membership.models import Member, MembershipPayment, MembershipYear
from school.models import Child, Family, SchoolPayment, SchoolYear
from treasury.models import TreasuryTransaction

SUMMARY_URL = "/api/kpi/summary/"
MOSQUES_URL = "/api/kpi/mosques/"


class TestKPIMosqueList(TestCase):
    """Tests du endpoint GET /api/kpi/mosques/."""

    def setUp(self):
        self.client = APIClient()
        Mosque.objects.create(name="Mosquée Alpha", slug="alpha", timezone="Europe/Paris")
        Mosque.objects.create(name="Mosquée Beta", slug="beta", timezone="Europe/Paris")

    def test_list_without_auth(self):
        """Liste publique — pas besoin d'être authentifié."""
        res = self.client.get(MOSQUES_URL)
        self.assertEqual(res.status_code, 200)

    def test_list_returns_all_mosques(self):
        res = self.client.get(MOSQUES_URL)
        slugs = [m["slug"] for m in res.data]
        self.assertIn("alpha", slugs)
        self.assertIn("beta", slugs)

    def test_list_contains_slug_and_name(self):
        res = self.client.get(MOSQUES_URL)
        item = res.data[0]
        self.assertIn("slug", item)
        self.assertIn("name", item)
        # Aucun PII : pas d'email, pas de phone
        self.assertNotIn("email", item)
        self.assertNotIn("phone", item)


class TestKPISummary(TestCase):
    """Tests du endpoint GET /api/kpi/summary/?mosque=<slug>."""

    def setUp(self):
        self.client = APIClient()
        self.mosque = Mosque.objects.create(
            name="Mosquée KPI Test",
            slug="kpi-test",
            timezone="Europe/Paris",
        )
        MosqueSettings.objects.get_or_create(
            mosque=self.mosque,
            defaults={
                "active_school_year_label": "2025-2026",
                "school_fee_default": 500,
                "membership_fee_amount": 50,
            },
        )

        # École
        self.school_year, _ = SchoolYear.objects.get_or_create(
            mosque=self.mosque, label="2025-2026",
            defaults={"start_date": "2025-09-01", "end_date": "2026-06-30", "is_active": True},
        )
        self.family1 = Family.objects.create(mosque=self.mosque, primary_contact_name="Famille1", phone1="0600000001")
        self.family2 = Family.objects.create(mosque=self.mosque, primary_contact_name="Famille2", phone1="0600000002")
        Child.objects.create(mosque=self.mosque, family=self.family1, first_name="Enfant1", level="CP")
        Child.objects.create(mosque=self.mosque, family=self.family1, first_name="Enfant2", level="CE1")
        Child.objects.create(mosque=self.mosque, family=self.family2, first_name="Enfant3", level="CP")
        SchoolPayment.objects.create(
            mosque=self.mosque, family=self.family1, school_year=self.school_year,
            amount=500, date="2026-01-15",
        )

        # Adhésion
        self.mbr_year, _ = MembershipYear.objects.get_or_create(
            mosque=self.mosque, year=2025,
            defaults={"amount_expected": 50, "is_active": True},
        )
        self.member1 = Member.objects.create(mosque=self.mosque, full_name="Membre1", phone="0600000010")
        self.member2 = Member.objects.create(mosque=self.mosque, full_name="Membre2", phone="0600000011")
        MembershipPayment.objects.create(
            mosque=self.mosque, member=self.member1, membership_year=self.mbr_year,
            amount=50, date="2026-01-15",
        )

        # Trésorerie
        today = date.today()
        TreasuryTransaction.objects.create(
            mosque=self.mosque, label="Don", direction="IN", amount=1000, date=today
        )
        TreasuryTransaction.objects.create(
            mosque=self.mosque, label="Charge", direction="OUT", amount=300, date=today
        )

    # ── Paramètres ─────────────────────────────────────────────────────────

    def test_missing_mosque_param(self):
        """Sans ?mosque= → 400."""
        res = self.client.get(SUMMARY_URL)
        self.assertEqual(res.status_code, 400)

    def test_unknown_slug(self):
        """Slug inconnu → 404."""
        res = self.client.get(f"{SUMMARY_URL}?mosque=slug-inconnu")
        self.assertEqual(res.status_code, 404)

    def test_accessible_without_auth(self):
        """Endpoint public — pas besoin d'être authentifié."""
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        self.assertEqual(res.status_code, 200)

    # ── Structure de la réponse ────────────────────────────────────────────

    def test_response_has_required_keys(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        self.assertEqual(res.status_code, 200)
        data = res.data
        self.assertIn("mosque", data)
        self.assertIn("school", data)
        self.assertIn("membership", data)
        self.assertIn("treasury", data)
        self.assertIn("campaigns", data)
        self.assertIn("generated_at", data)

    def test_school_keys(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        school = res.data["school"]
        for key in ("total_families", "total_children", "by_level",
                    "active_year", "amount_paid", "families_paid", "families_unpaid"):
            self.assertIn(key, school, msg=f"Clé manquante : school.{key}")

    def test_membership_keys(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        mbr = res.data["membership"]
        for key in ("total_members", "members_paid", "members_unpaid",
                    "total_collected", "active_year", "amount_expected_per_member"):
            self.assertIn(key, mbr, msg=f"Clé manquante : membership.{key}")

    def test_treasury_keys(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        treas = res.data["treasury"]
        for key in ("total_in", "total_out", "balance", "period", "by_category"):
            self.assertIn(key, treas, msg=f"Clé manquante : treasury.{key}")

    # ── Aucun PII ──────────────────────────────────────────────────────────

    def test_no_pii_in_response(self):
        """La réponse ne doit contenir aucun nom de famille ou téléphone."""
        import json
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        body = json.dumps(res.data)
        # Les noms de familles et membres ne doivent pas apparaître
        self.assertNotIn("Famille1", body)
        self.assertNotIn("Membre1", body)
        # Numéros de téléphone
        self.assertNotIn("0600000001", body)
        self.assertNotIn("0600000010", body)

    # ── Agrégats ──────────────────────────────────────────────────────────

    def test_school_total_children(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        self.assertEqual(res.data["school"]["total_children"], 3)

    def test_school_total_families(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        self.assertEqual(res.data["school"]["total_families"], 2)

    def test_school_families_paid_and_unpaid(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        school = res.data["school"]
        self.assertEqual(school["families_paid"], 1)    # family1 a payé
        self.assertEqual(school["families_unpaid"], 1)  # family2 n'a pas payé

    def test_school_by_level(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        by_level = res.data["school"]["by_level"]
        self.assertEqual(by_level.get("CP"), 2)
        self.assertEqual(by_level.get("CE1"), 1)

    def test_membership_totals(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        mbr = res.data["membership"]
        self.assertEqual(mbr["total_members"], 2)
        self.assertEqual(mbr["members_paid"], 1)
        self.assertEqual(mbr["members_unpaid"], 1)
        self.assertEqual(float(mbr["total_collected"]), 50.0)

    def test_treasury_totals(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        treas = res.data["treasury"]
        self.assertEqual(float(treas["total_in"]), 1000.0)
        self.assertEqual(float(treas["total_out"]), 300.0)
        self.assertAlmostEqual(float(treas["balance"]), 700.0, places=2)

    def test_mosque_name_in_response(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test")
        self.assertEqual(res.data["mosque"], "Mosquée KPI Test")

    # ── Filtre par mois ────────────────────────────────────────────────────

    def test_treasury_month_filter_returns_zero_for_past_month(self):
        """Un mois sans transaction doit retourner 0 en entrée/sortie."""
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test&month=2000-01")
        self.assertEqual(res.status_code, 200)
        treas = res.data["treasury"]
        self.assertEqual(float(treas["total_in"]), 0.0)
        self.assertEqual(float(treas["total_out"]), 0.0)
        self.assertEqual(float(treas["balance"]), 0.0)

    def test_treasury_month_filter_invalid_format_uses_current(self):
        """Un format ?month= invalide ne doit pas crasher le serveur."""
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test&month=invalid")
        self.assertEqual(res.status_code, 200)

    def test_treasury_period_label_matches_month_param(self):
        res = self.client.get(f"{SUMMARY_URL}?mosque=kpi-test&month=2000-01")
        self.assertEqual(res.data["treasury"]["period"], "2000-01")

    # ── Isolation multi-tenant ─────────────────────────────────────────────

    def test_other_mosque_sees_zero_data(self):
        """Une autre mosquée sans données retourne des compteurs à 0."""
        Mosque.objects.create(name="Vide", slug="vide", timezone="Europe/Paris")
        res = self.client.get(f"{SUMMARY_URL}?mosque=vide")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["school"]["total_children"], 0)
        self.assertEqual(res.data["membership"]["total_members"], 0)
        self.assertEqual(float(res.data["treasury"]["total_in"]), 0.0)
