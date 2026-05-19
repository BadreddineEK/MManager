"""
Injection directe des 38 paiements de cotisation manquants (Janv/Fév 2026)
via ORM Django dans le container backend-prod.

Usage (sur le Pi) :
    docker exec mmanager-backend-prod-1 python /scripts/inject_membership_payments.py

Le script est IDEMPOTENT : il ne crée pas de doublon si le paiement existe déjà
(même membre, même date, même montant).
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, "/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django_tenants.utils import schema_context
from membership.models import Member, MembershipYear, MembershipPayment
from core.models import Mosque

# ── Configuration ──────────────────────────────────────────────────────────────
TENANT_SCHEMA = "mosk_okba_ibn_nafaa"   # schema postgres du tenant
MOSQUE_DOMAIN = "mosk-okba-ibn-nafaa.nidham.fr"
YEAR = 2026

# ── Paiements à injecter ───────────────────────────────────────────────────────
PAYMENTS = [
    {"member": "BEL HADJ Nail",          "date": "2026-01-01", "amount": 15.0},
    {"member": "BEL HADJ Nail",          "date": "2026-02-01", "amount": 15.0},
    {"member": "BELLOUTI Khalid",         "date": "2026-01-01", "amount": 13.0},
    {"member": "BENCHAABANE Abdelkader", "date": "2026-01-01", "amount": 33.0},
    {"member": "BENTALEB Ridha",          "date": "2026-01-01", "amount": 30.0},
    {"member": "BENTALEB Ridha",          "date": "2026-02-01", "amount": 30.0},
    {"member": "CHBANI Hicham",           "date": "2026-01-01", "amount": 13.0},
    {"member": "CHBANI Hicham",           "date": "2026-02-01", "amount": 13.0},
    {"member": "CHTIOUI Karim",           "date": "2026-01-01", "amount": 20.0},
    {"member": "CHTIOUI Karim",           "date": "2026-02-01", "amount": 20.0},
    {"member": "CHTIOUI Nordine",         "date": "2026-01-01", "amount": 30.0},
    {"member": "DAAS Foued",              "date": "2026-01-01", "amount": 13.0},
    {"member": "DAAS Foued",              "date": "2026-02-01", "amount": 13.0},
    {"member": "DHEHIBI Talel",           "date": "2026-01-01", "amount": 10.0},
    {"member": "DHEHIBI Talel",           "date": "2026-02-01", "amount": 110.0},
    {"member": "DZIRI Mokhtar",           "date": "2026-01-01", "amount": 10.0},
    {"member": "DZIRI Mokhtar",           "date": "2026-02-01", "amount": 10.0},
    {"member": "DZIRI Mokhtar Fils",      "date": "2026-01-01", "amount": 15.0},
    {"member": "DZIRI Mokhtar Fils",      "date": "2026-02-01", "amount": 15.0},
    {"member": "EL AMRANI Mohammed",      "date": "2026-01-01", "amount": 21.0},
    {"member": "EL MAROUDI Marouane",     "date": "2026-01-01", "amount": 20.0},
    {"member": "EL MAROUDI Marouane",     "date": "2026-02-01", "amount": 20.0},
    {"member": "HABI Mouloud",            "date": "2026-01-01", "amount": 72.0},
    {"member": "HABI Mouloud",            "date": "2026-02-01", "amount": 50.0},
    {"member": "HABI Morgiane",           "date": "2026-01-01", "amount": 70.0},
    {"member": "HAJJI Mimoun",            "date": "2026-01-01", "amount": 50.0},
    {"member": "KACHER Yamine",           "date": "2026-01-01", "amount": 20.0},
    {"member": "KACHER Yamine",           "date": "2026-02-01", "amount": 20.0},
    {"member": "KALIFA Amor",             "date": "2026-01-01", "amount": 20.0},
    {"member": "KALIFA Amor",             "date": "2026-02-01", "amount": 20.0},
    {"member": "KECIR Houssine",          "date": "2026-01-01", "amount": 50.0},
    {"member": "KECIR Houssine",          "date": "2026-02-01", "amount": 50.0},
    {"member": "SLITI Brahim",            "date": "2026-01-01", "amount": 12.5},
    {"member": "SLITI Brahim",            "date": "2026-02-01", "amount": 12.5},
    {"member": "SMIDA Abdessatar",        "date": "2026-01-01", "amount": 13.0},
    {"member": "SMIDA Abdessatar",        "date": "2026-02-01", "amount": 13.0},
    {"member": "SMIDA Laid",              "date": "2026-01-01", "amount": 15.0},
    {"member": "SMIDA Laid",             "date": "2026-02-01", "amount": 80.0},
]

# ── Helpers ────────────────────────────────────────────────────────────────────
def norm(s):
    return (s or "").strip().lower()

# ── Exécution dans le schema tenant ───────────────────────────────────────────
with schema_context(TENANT_SCHEMA):
    # 1. Récupérer la mosquée
    mosque = Mosque.objects.filter(schema_name=TENANT_SCHEMA).first()
    if not mosque:
        print(f"❌ Mosquée introuvable pour schema '{TENANT_SCHEMA}'")
        sys.exit(1)
    print(f"✅ Mosquée : {mosque.name}")

    # 2. Récupérer ou créer l'année 2026
    membership_year, created = MembershipYear.objects.get_or_create(
        mosque=mosque,
        year=YEAR,
        defaults={"amount_expected": 0, "is_active": True},
    )
    if created:
        print(f"⚠️  MembershipYear {YEAR} créée (amount_expected=0, pensez à la configurer)")
    else:
        print(f"✅ MembershipYear {YEAR} trouvée (montant attendu : {membership_year.amount_expected}€)")

    # 3. Pré-charger les membres en dict normalisé
    members_dict = {}
    for m in Member.objects.filter(mosque=mosque):
        full = norm(f"{m.last_name} {m.first_name}")
        full2 = norm(f"{m.first_name} {m.last_name}")
        members_dict[full] = m
        members_dict[full2] = m
        # Aussi indexer par last_name seul pour les noms composés
        members_dict[norm(m.last_name)] = m

    print(f"✅ {len(Member.objects.filter(mosque=mosque))} adhérents chargés en mémoire\n")

    # 4. Injecter les paiements
    success = skipped = errors = 0

    for p in PAYMENTS:
        name = p["member"]
        date_str = p["date"]
        amount = p["amount"]

        # Résolution membre : essayer "NOM Prénom" et "NOM" seul
        member = members_dict.get(norm(name))
        if not member:
            # Chercher par last_name exact (cas "DZIRI Mokhtar Fils" → last_name="DZIRI Mokhtar Fils" ou split)
            parts = name.strip().split()
            # Tenter last_name = tout sauf le dernier mot, first_name = dernier mot
            if len(parts) >= 2:
                candidate_ln = " ".join(parts[:-1])
                candidate_fn = parts[-1]
                member = Member.objects.filter(
                    mosque=mosque,
                    last_name__iexact=candidate_ln,
                    first_name__iexact=candidate_fn,
                ).first()
            if not member:
                # Tenter last_name = premier mot, first_name = reste
                candidate_ln2 = parts[0]
                candidate_fn2 = " ".join(parts[1:])
                member = Member.objects.filter(
                    mosque=mosque,
                    last_name__iexact=candidate_ln2,
                    first_name__iexact=candidate_fn2,
                ).first()

        if not member:
            print(f"  ❌ Membre introuvable : '{name}'")
            errors += 1
            continue

        # Idempotence : ne pas dupliquer si déjà présent
        existing = MembershipPayment.objects.filter(
            mosque=mosque,
            member=member,
            membership_year=membership_year,
            date=date_str,
            amount=amount,
        ).first()
        if existing:
            print(f"  ⏭  Déjà en base : {name} {date_str} {amount}€")
            skipped += 1
            continue

        MembershipPayment.objects.create(
            mosque=mosque,
            member=member,
            membership_year=membership_year,
            date=date_str,
            amount=amount,
            method="virement",
            status="validated",
            note="Import Janv-Fév 2026",
        )
        print(f"  ✅ Créé : {name} {date_str} {amount}€")
        success += 1

    print(f"\n{'='*50}")
    print(f"RÉSULTAT : {success} créés | {skipped} doublons ignorés | {errors} erreurs")
    print(f"{'='*50}")

    if errors > 0:
        print("\n⚠️  Pour les membres introuvables, vérifiez l'orthographe exacte avec :")
        print(f"   docker exec mmanager-backend-prod-1 python -c \"")
        print(f"   import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup()")
        print(f"   from django_tenants.utils import schema_context")
        print(f"   from membership.models import Member")
        print(f"   with schema_context('{TENANT_SCHEMA}'):")
        print(f"       [print(m.last_name, '|', m.first_name) for m in Member.objects.all()]\"")
