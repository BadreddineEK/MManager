"""
seed_test_tenant — Peuple un tenant avec des données fictives réalistes.

Usage :
    python manage.py seed_test_tenant --schema mosquee-test

Crée :
  - MosqueSettings configurés (niveaux, tarifs, barème progressif)
  - 1 admin + 1 trésorier + 1 responsable école
  - 8 familles, 14 enfants répartis sur tous les niveaux
  - 12 adhérents (mélange à jour / en retard / périodicités variées)
  - ~50 transactions de trésorerie (dons, cotisations, loyer, salaires, factures)
  - 2 cagnottes actives
  - 1 compte bancaire
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from core.models import Mosque


class Command(BaseCommand):
    help = "Peuple un tenant existant avec des données fictives pour les tests"

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True, help="schema_name du tenant à peupler")
        parser.add_argument("--flush", action="store_true", help="Vider les données existantes avant de seeder")

    def handle(self, *args, **options):
        schema = options["schema"]
        try:
            mosque = Mosque.objects.get(schema_name=schema)
        except Mosque.DoesNotExist:
            raise CommandError(f"Tenant '{schema}' introuvable. Créez-le d'abord avec create_tenant.")

        self.stdout.write(f"→ Seeding tenant : {mosque.name} (schema: {schema})")

        with schema_context(schema):
            self._seed(mosque, flush=options["flush"])

        self.stdout.write(self.style.SUCCESS(f"✓ Seed terminé pour '{schema}'"))

    # ──────────────────────────────────────────────────────────────────────────
    def _seed(self, mosque, flush=False):
        from django.contrib.auth import get_user_model
        from core.models import MosqueSettings
        from school.models import Family, Child, SchoolYear, SchoolPayment
        from membership.models import Member, MembershipYear, MembershipPayment
        from treasury.models import TreasuryTransaction, BankAccount
        try:
            from campaigns.models import Campaign
            has_campaigns = True
        except ImportError:
            has_campaigns = False

        User = get_user_model()

        if flush:
            self.stdout.write("  Vidage des données existantes…")
            TreasuryTransaction.objects.all().delete()
            MembershipPayment.objects.all().delete()
            MembershipYear.objects.all().delete()
            Member.objects.all().delete()
            SchoolPayment.objects.all().delete()
            Child.objects.all().delete()
            Family.objects.all().delete()
            SchoolYear.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        # ── 1. Settings ──────────────────────────────────────────────────────
        self.stdout.write("  1/7 · Settings…")
        settings, _ = MosqueSettings.objects.get_or_create(mosque=mosque)
        settings.mosque_name              = "Mosquée Al-Nour (TEST)"
        settings.mosque_timezone          = "Europe/Paris"
        settings.school_levels            = ["NP", "N1", "N2", "N3", "N4", "N5", "N6"]
        settings.school_fee_default       = Decimal("300.00")
        settings.school_fee_mode          = "annual"
        settings.school_fee_tiers         = {"1": 300, "2": 390, "3": 450, "4+": 500}
        settings.membership_fee_amount    = Decimal("100.00")
        settings.membership_fee_mode      = "per_person"
        settings.membership_school_rule   = "separate"
        settings.membership_school_discount = Decimal("0")
        settings.active_school_year_label = "2025-2026"
        settings.receipt_address          = "12 rue des Lilas\n01000 Bourg-en-Bresse"
        settings.receipt_phone            = "04 74 00 00 00"
        settings.receipt_legal_mention    = "Association loi 1901 — Don déductible à 66% (art. 200 CGI)."
        settings.show_kpi_school          = True
        settings.show_kpi_membership      = True
        settings.show_kpi_treasury        = True
        settings.show_kpi_campaigns       = True
        settings.save()

        # ── 2. Utilisateurs ──────────────────────────────────────────────────
        self.stdout.write("  2/7 · Utilisateurs…")
        _user(User, "admin@test.mosquee", "Admin123!", "ADMIN",     "Kenza Admin",     mosque)
        _user(User, "tresor@test.mosquee", "Admin123!", "TRESORIER", "Bilal Trésorier", mosque)
        _user(User, "ecole@test.mosquee",  "Admin123!", "ECOLE_MANAGER", "Fatima École", mosque)

        # ── 3. Année scolaire ────────────────────────────────────────────────
        self.stdout.write("  3/7 · École (familles, enfants, paiements)…")
        year, _ = SchoolYear.objects.get_or_create(
            mosque=mosque, label="2025-2026",
            defaults={"start_date": date(2025, 9, 1), "end_date": date(2026, 6, 30), "is_active": True}
        )

        # Familles fictives
        FAMILLES = [
            ("Benali",    "Youssef Benali",    "06 10 11 22 33", "ybenali@mail.fr",    "5 rue du Parc, 01000",    ["Omar", "Yasmine"]),
            ("Mansouri",  "Rachid Mansouri",   "06 20 33 44 55", "rmansouri@mail.fr",  "8 av. Gambetta, 01000",  ["Amina"]),
            ("Khalid",    "Hassan Khalid",     "06 30 44 55 66", "hkhalid@mail.fr",    "14 bd du Lac, 01100",    ["Ines", "Karim", "Sara"]),
            ("Ouahbi",    "Nadia Ouahbi",      "06 40 55 66 77", "nouahbi@mail.fr",    "2 impasse Verte, 01200", ["Adam"]),
            ("Ferhat",    "Mourad Ferhat",     "06 50 66 77 88", "mferhat@mail.fr",    "9 rue Nationale, 01100", ["Douaa", "Mehdi"]),
            ("Touati",    "Leila Touati",      "06 60 77 88 99", "ltouati@mail.fr",    "7 sq. des Roses, 01000", ["Sami", "Rim"]),
            ("Bouzid",    "Karim Bouzid",      "06 70 88 99 00", "kbouzid@mail.fr",    "3 rue Neuve, 01300",     ["Nour"]),
            ("Hammadi",   "Souad Hammadi",     "06 80 99 00 11", "shammadi@mail.fr",   "16 rue Voltaire, 01000", ["Tarek", "Lina"]),
        ]
        LEVELS = ["NP", "N1", "N2", "N3", "N4", "N5", "N6"]
        level_idx = 0
        family_objs = []
        for (fname, contact, phone, email, addr, children_names) in FAMILLES:
            fam, _ = Family.objects.get_or_create(
                mosque=mosque, primary_contact_name=contact,
                defaults={"phone1": phone, "email": email, "address": addr}
            )
            family_objs.append((fam, len(children_names)))
            for cname in children_names:
                child, _ = Child.objects.get_or_create(
                    mosque=mosque, first_name=cname, family=fam,
                    defaults={"birth_date": date(2015, random.randint(1,12), random.randint(1,28)),
                              "level": LEVELS[level_idx % len(LEVELS)]}
                )
                level_idx += 1
                # Paiement école (70% payés)
                if random.random() < 0.70:
                    SchoolPayment.objects.get_or_create(
                        mosque=mosque, school_year=year, family=fam, child=child,
                        defaults={
                            "date":   date(2025, random.randint(9,12), random.randint(1,28)),
                            "amount": Decimal(str(settings.school_fee_default)),
                            "method": random.choice(["virement", "cash", "cheque"]),
                        }
                    )

        # ── 4. Adhérents ─────────────────────────────────────────────────────
        self.stdout.write("  4/7 · Adhérents…")
        MEMBRES = [
            ("Mohamed Amine Bensaid",    "06 11 22 33 44", "mbensaid@mail.fr",    "annual",    "virement",   True),
            ("Fatima Zahra Idrissi",     "06 22 33 44 55", "fidrissi@mail.fr",    "annual",    "virement",   True),
            ("Abdelhak Bouras",          "06 33 44 55 66", "abouras@mail.fr",     "quarterly", "cash",       True),
            ("Khadija Rahali",           "06 44 55 66 77", "krahali@mail.fr",     "monthly",   "prelevement",True),
            ("Youssef Zouaoui",          "06 55 66 77 88", "yzouaoui@mail.fr",    "annual",    "cheque",     False),
            ("Nadia Belkacem",           "06 66 77 88 99", "nbelkacem@mail.fr",   "biannual",  "virement",   True),
            ("Omar El Fassi",            "06 77 88 99 00", "oelfassi@mail.fr",    "annual",    "virement",   False),
            ("Samira Hadjadj",           "06 88 99 00 11", "shadjadj@mail.fr",    "quarterly", "cash",       True),
            ("Rachid Aouad",             "06 99 00 11 22", "raouad@mail.fr",      "annual",    "virement",   True),
            ("Leila Mimouni",            "06 00 11 22 33", "lmimouni@mail.fr",    "monthly",   "prelevement",False),
            ("Badr Chaouki",             "06 12 34 56 78", "bchaouki@mail.fr",    "annual",    "virement",   True),
            ("Aicha Tounsi",             "06 23 45 67 89", "atounsi@mail.fr",     "biannual",  "cheque",     True),
        ]
        mship_year, _ = MembershipYear.objects.get_or_create(
            mosque=mosque, year=2025,
            defaults={"amount_expected": Decimal("100.00")}
        )
        member_objs = []
        for (name, phone, email, freq, method, paid) in MEMBRES:
            m, _ = Member.objects.get_or_create(
                mosque=mosque, full_name=name,
                defaults={
                    "phone": phone, "email": email,
                    "payment_frequency": freq, "payment_method": method,
                }
            )
            member_objs.append(m)
            if paid:
                MembershipPayment.objects.get_or_create(
                    mosque=mosque, member=m, membership_year=mship_year,
                    defaults={
                        "date":   date(2025, random.randint(1, 6), random.randint(1, 28)),
                        "amount": Decimal("100.00"),
                        "method": method,
                    }
                )

        # ── 5. Compte bancaire ───────────────────────────────────────────────
        self.stdout.write("  5/7 · Compte bancaire…")
        bank_acc = None
        if hasattr(TreasuryTransaction, "bank_account"):
            bank_acc, _ = BankAccount.objects.get_or_create(
                mosque=mosque, label="Compte principal (1901)",
                defaults={"account_number": "FR76 1234 5678 9012 3456 7890 123", "regime": "1901"}
            )

        # ── 6. Transactions trésorerie ───────────────────────────────────────
        self.stdout.write("  6/7 · Trésorerie (~50 transactions)…")
        TRANSACTIONS = []
        # Dons du vendredi (chaque vendredi depuis sept 2025)
        d = date(2025, 9, 5)
        while d <= date(2026, 4, 30):
            TRANSACTIONS.append(dict(
                date=d, label=f"Don vendredi {d.strftime('%d/%m/%Y')}",
                category="don", direction="IN",
                amount=Decimal(str(random.randint(80, 350))),
                method="cash", regime_fiscal="1905",
            ))
            d += timedelta(days=7)

        # Loyer mensuel
        for m_num in range(9, 13):
            TRANSACTIONS.append(dict(
                date=date(2025, m_num, 1), label="Loyer salle de prière",
                category="loyer", direction="OUT",
                amount=Decimal("850.00"), method="virement", regime_fiscal="1905",
            ))
        for m_num in range(1, 5):
            TRANSACTIONS.append(dict(
                date=date(2026, m_num, 1), label="Loyer salle de prière",
                category="loyer", direction="OUT",
                amount=Decimal("850.00"), method="virement", regime_fiscal="1905",
            ))

        # Salaires imam + enseignant
        for m_num in range(9, 13):
            TRANSACTIONS.append(dict(
                date=date(2025, m_num, 28), label="Salaire Imam Abdelkader",
                category="salaire", direction="OUT",
                amount=Decimal("1200.00"), method="virement", regime_fiscal="1905",
            ))
            TRANSACTIONS.append(dict(
                date=date(2025, m_num, 28), label="Honoraires enseignant école",
                category="salaire", direction="OUT",
                amount=Decimal("400.00"), method="virement", regime_fiscal="1901",
            ))

        # Factures EDF, eau, assurance
        FACTURES = [
            (date(2025, 10, 15), "Facture EDF Oct", "300.00"),
            (date(2025, 12, 15), "Facture EDF Déc", "420.00"),
            (date(2026, 2, 15),  "Facture EDF Fév", "390.00"),
            (date(2025, 11, 5),  "Eau SAUR",         "55.00"),
            (date(2026, 3, 5),   "Eau SAUR",         "60.00"),
            (date(2025, 9, 20),  "Allianz assurance","580.00"),
        ]
        for (dt, lbl, amt) in FACTURES:
            TRANSACTIONS.append(dict(
                date=dt, label=lbl, category="facture", direction="OUT",
                amount=Decimal(amt), method="virement", regime_fiscal="1901",
            ))

        # Subvention mairie
        TRANSACTIONS.append(dict(
            date=date(2025, 10, 3), label="Subvention Mairie 2025",
            category="subvention", direction="IN",
            amount=Decimal("2000.00"), method="virement", regime_fiscal="1901",
        ))

        # Cotisations adhérents (10 sur 12 payées)
        for m in member_objs[:10]:
            TRANSACTIONS.append(dict(
                date=date(2025, random.randint(1,6), random.randint(1,28)),
                label=f"Cotisation — {m.full_name}",
                category="cotisation", direction="IN",
                amount=Decimal("100.00"), method="virement", regime_fiscal="1901",
            ))

        # Paiements école (famille)
        for (fam, n_children) in family_objs[:6]:
            tiers = {1: 300, 2: 390, 3: 450}
            amt = Decimal(str(tiers.get(n_children, 450)))
            TRANSACTIONS.append(dict(
                date=date(2025, random.randint(9,11), random.randint(1,28)),
                label=f"École — {fam.primary_contact_name}",
                category="ecole", direction="IN",
                amount=amt, method=random.choice(["cash", "cheque", "virement"]),
                regime_fiscal="1901",
            ))

        # Travaux (projet)
        TRANSACTIONS.append(dict(
            date=date(2026, 1, 15), label="Travaux peinture salle",
            category="projet", direction="OUT",
            amount=Decimal("1800.00"), method="cheque", regime_fiscal="1905",
        ))

        for tx_data in TRANSACTIONS:
            TreasuryTransaction.objects.get_or_create(
                mosque=mosque,
                date=tx_data["date"],
                label=tx_data["label"],
                defaults={
                    "category":       tx_data["category"],
                    "direction":      tx_data["direction"],
                    "amount":         tx_data["amount"],
                    "method":         tx_data.get("method", "virement"),
                    "regime_fiscal":  tx_data.get("regime_fiscal", "1901"),
                }
            )

        # ── 7. Cagnottes ────────────────────────────────────────────────────
        if has_campaigns:
            self.stdout.write("  7/7 · Cagnottes…")
            Campaign = __import__("campaigns.models", fromlist=["Campaign"]).Campaign
            Campaign.objects.get_or_create(
                name="Rénovation climatisation",
                defaults={
                    "icon": "❄️", "goal": Decimal("5000.00"),
                    "collected": Decimal("1250.00"), "is_active": True,
                    "description": "Remplacement des climatiseurs de la salle principale.",
                }
            )
            Campaign.objects.get_or_create(
                name="Achat tapis de prière",
                defaults={
                    "icon": "🕌", "goal": Decimal("1200.00"),
                    "collected": Decimal("870.00"), "is_active": True,
                    "description": "Nouveaux tapis pour la salle des hommes.",
                }
            )
        else:
            self.stdout.write("  7/7 · Cagnottes (module non disponible, ignoré)")

        # Résumé
        from school.models import Family as F, Child as C, SchoolPayment as SP
        from membership.models import Member as Me, MembershipPayment as MP
        from treasury.models import TreasuryTransaction as TX
        self.stdout.write(self.style.SUCCESS(
            f"\n  ✓ Résumé :"
            f"\n    Familles     : {F.objects.count()}"
            f"\n    Enfants      : {C.objects.count()} (dont {SP.objects.count()} paiements école)"
            f"\n    Adhérents    : {Me.objects.count()} (dont {MP.objects.count()} cotisations payées)"
            f"\n    Transactions : {TX.objects.count()}"
        ))


def _user(User, email, password, role, full_name, mosque):
    """Crée ou met à jour un utilisateur dans le tenant courant.
    Le username est préfixé avec le schema (ex: mosquee-test__admin@test.mosquee)
    car le serializer JWT ajoute ce préfixe automatiquement à la connexion.
    """
    from django.db import connection as _conn
    schema = _conn.schema_name  # ex: "mosquee-test"
    username = f"{schema}__{email}"
    parts = full_name.split(" ", 1)
    first = parts[0]
    last  = parts[1] if len(parts) > 1 else ""
    u, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email, "first_name": first, "last_name": last,
            "role": role, "mosque": mosque, "is_active": True,
        }
    )
    # Toujours forcer le mot de passe (même si user déjà existant)
    u.set_password(password)
    u.save()
    return u
