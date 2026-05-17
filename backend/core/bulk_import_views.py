"""
POST /api/admin/import/bulk
===========================
Endpoint d'import en masse pour migration de données historiques.
Insère familles, enfants, paiements école, adhérents, cotisations
et transactions trésorerie en un seul appel JSON.

Comportement :
- Tolérance aux erreurs : une ligne KO → errors[], import continue
- Idempotence : upsert sur clés naturelles (pas de doublons au 2e appel)
- Transaction atomique par bloc (familles, enfants, etc.)
- Rollback partiel : si transactions plante, familles/enfants restent
"""
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import BankAccount
from membership.models import Member, MembershipPayment, MembershipYear
from school.models import Child, Family, SchoolPayment, SchoolYear
from treasury.models import TreasuryTransaction

logger = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _norm(s):
    """Normalise une chaîne pour comparaison : strip + lowercase."""
    return (s or "").strip().lower()


def _parse_date(val, ligne, entite, errors):
    """Parse une date ISO 8601 ou dd/mm/yyyy. Retourne None si invalide."""
    if not val:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    errors.append({"entite": entite, "ligne": ligne,
                   "raison": f"Date invalide : '{val}'"})
    return None


def _parse_amount(val, ligne, entite, errors):
    """Parse un montant décimal. Retourne None si invalide."""
    try:
        return Decimal(str(val).replace(",", ".").strip())
    except (InvalidOperation, TypeError):
        errors.append({"entite": entite, "ligne": ligne,
                       "raison": f"Montant invalide : '{val}'"})
        return None


METHOD_MAP = {
    "vir": "virement", "virement": "virement",
    "esp": "cash",     "especes": "cash",   "espèces": "cash", "cash": "cash",
    "chq": "cheque",   "cheq": "cheque",    "chèq": "cheque",
    "chèque": "cheque","cheque": "cheque",
}


def _parse_method(val):
    return METHOD_MAP.get(_norm(val), "autre")


STATUS_MAP = {
    "validé": "validated", "valide": "validated", "validated": "validated",
    "ok": "validated",
    "en attente": "pending", "pending": "pending", "attente": "pending",
}


def _parse_status(val):
    return STATUS_MAP.get(_norm(val), "validated")


# ─── Blocs d'import ───────────────────────────────────────────────────────────

def _import_familles(mosque, rows):
    inserted = 0
    errors = []
    family_map = {}  # norm_name → Family instance

    try:
        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                nom = (row.get("nom") or "").strip()
                if not nom:
                    errors.append({"entite": "familles", "ligne": i,
                                   "raison": "Champ 'nom' manquant"})
                    continue
                try:
                    obj = Family.objects.filter(
                        mosque=mosque,
                        primary_contact_name__iexact=nom,
                    ).first()
                    if obj is None:
                        obj = Family.objects.create(
                            mosque=mosque,
                            primary_contact_name=nom,
                            phone1=  (row.get("telephone") or "").strip(),
                            phone2=  (row.get("telephone2") or "").strip(),
                            email=   (row.get("email") or "").strip(),
                            address= (row.get("adresse") or "").strip(),
                        )
                        inserted += 1
                    family_map[_norm(nom)] = obj
                except Exception as e:
                    errors.append({"entite": "familles", "ligne": i,
                                   "raison": str(e)})
    except Exception as e:
        errors.append({"entite": "familles", "ligne": 0,
                       "raison": f"Erreur bloc : {e}"})

    # Charger aussi les familles déjà en base (pour les blocs suivants)
    for f in Family.objects.filter(mosque=mosque):
        family_map[_norm(f.primary_contact_name)] = f

    return inserted, errors, family_map


def _import_enfants(mosque, rows, family_map):
    inserted = 0
    errors = []
    child_map = {}  # (norm_famille, norm_prenom) → Child

    try:
        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                nom_famille = (row.get("nom_famille") or "").strip()
                prenom = (row.get("prenom") or "").strip()
                if not nom_famille or not prenom:
                    errors.append({"entite": "enfants", "ligne": i,
                                   "raison": "Champs 'nom_famille' ou 'prenom' manquants"})
                    continue

                famille = family_map.get(_norm(nom_famille))
                if not famille:
                    errors.append({"entite": "enfants", "ligne": i,
                                   "raison": f"Famille '{nom_famille}' non trouvée"})
                    continue

                birth_date = _parse_date(row.get("date_naissance"), i, "enfants", errors)
                niveau = (row.get("niveau") or "").strip()

                try:
                    obj = Child.objects.filter(
                        mosque=mosque,
                        family=famille,
                        first_name__iexact=prenom,
                    ).first()
                    if obj is None:
                        obj = Child.objects.create(
                            mosque=mosque,
                            family=famille,
                            first_name=prenom,
                            birth_date=birth_date,
                            level=niveau,
                        )
                        inserted += 1
                    child_map[(_norm(nom_famille), _norm(prenom))] = obj
                except Exception as e:
                    errors.append({"entite": "enfants", "ligne": i,
                                   "raison": str(e)})
    except Exception as e:
        errors.append({"entite": "enfants", "ligne": 0,
                       "raison": f"Erreur bloc : {e}"})

    # Charger aussi les enfants déjà en base
    for c in Child.objects.filter(mosque=mosque).select_related("family"):
        child_map[(_norm(c.family.primary_contact_name), _norm(c.first_name))] = c

    return inserted, errors, child_map


def _get_or_create_school_year(mosque, label):
    """Retourne l'année scolaire active ou en crée une par défaut."""
    if label:
        obj, _ = SchoolYear.objects.get_or_create(
            mosque=mosque,
            label=label,
            defaults={
                "start_date": date(int(label[:4]), 9, 1),
                "end_date":   date(int(label[:4]) + 1, 6, 30),
                "is_active":  False,
            },
        )
        return obj
    return SchoolYear.objects.filter(mosque=mosque, is_active=True).first()


def _import_paiements_ecole(mosque, rows, family_map, child_map):
    inserted = 0
    errors = []
    school_year_cache = {}

    try:
        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                nom_famille  = (row.get("nom_famille") or "").strip()
                prenom_enfant = (row.get("prenom_enfant") or "").strip()
                date_val     = _parse_date(row.get("date"), i, "paiements_ecole", errors)
                montant      = _parse_amount(row.get("montant"), i, "paiements_ecole", errors)

                if not nom_famille or date_val is None or montant is None:
                    errors.append({"entite": "paiements_ecole", "ligne": i,
                                   "raison": "Champs obligatoires manquants (nom_famille, date, montant)"})
                    continue

                famille = family_map.get(_norm(nom_famille))
                if not famille:
                    errors.append({"entite": "paiements_ecole", "ligne": i,
                                   "raison": f"Famille '{nom_famille}' non trouvée"})
                    continue

                child = child_map.get((_norm(nom_famille), _norm(prenom_enfant))) if prenom_enfant else None
                if prenom_enfant and not child:
                    errors.append({"entite": "paiements_ecole", "ligne": i,
                                   "raison": f"Enfant '{prenom_enfant}' non trouvé dans famille '{nom_famille}'"})
                    continue

                # Année scolaire : déduire depuis la date si non fournie
                annee_label = (row.get("annee_scolaire") or "").strip()
                if not annee_label:
                    y = date_val.year
                    m = date_val.month
                    annee_label = f"{y}-{y+1}" if m >= 9 else f"{y-1}-{y}"

                if annee_label not in school_year_cache:
                    school_year_cache[annee_label] = _get_or_create_school_year(mosque, annee_label)
                school_year = school_year_cache[annee_label]

                try:
                    existing = SchoolPayment.objects.filter(
                        mosque=mosque,
                        family=famille,
                        child=child,
                        date=date_val,
                        amount=montant,
                    ).first()
                    if existing is None:
                        SchoolPayment.objects.create(
                            mosque=mosque,
                            family=famille,
                            child=child,
                            date=date_val,
                            amount=montant,
                            school_year=school_year,
                            method= _parse_method(row.get("mode_paiement")),
                            status= _parse_status(row.get("statut")),
                            note=   (row.get("note") or "").strip(),
                        )
                        inserted += 1
                except Exception as e:
                    errors.append({"entite": "paiements_ecole", "ligne": i,
                                   "raison": str(e)})
    except Exception as e:
        errors.append({"entite": "paiements_ecole", "ligne": 0,
                       "raison": f"Erreur bloc : {e}"})

    return inserted, errors


def _import_adherents(mosque, rows):
    inserted = 0
    errors = []
    member_map = {}  # norm_full_name → Member

    try:
        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                nom    = (row.get("nom") or "").strip()
                prenom = (row.get("prenom") or "").strip()
                if not nom:
                    errors.append({"entite": "adherents", "ligne": i,
                                   "raison": "Champ 'nom' manquant"})
                    continue

                full_name = f"{nom} {prenom}".strip() if prenom else nom

                try:
                    obj = Member.objects.filter(
                        mosque=mosque,
                        full_name__iexact=full_name,
                    ).first()
                    if obj is None:
                        obj = Member.objects.create(
                            mosque=mosque,
                            full_name=full_name,
                            phone=   (row.get("telephone") or "").strip(),
                            email=   (row.get("email") or "").strip(),
                            address= (row.get("adresse") or "").strip(),
                        )
                        inserted += 1
                    member_map[_norm(full_name)] = obj
                except Exception as e:
                    errors.append({"entite": "adherents", "ligne": i,
                                   "raison": str(e)})
    except Exception as e:
        errors.append({"entite": "adherents", "ligne": 0,
                       "raison": f"Erreur bloc : {e}"})

    for m in Member.objects.filter(mosque=mosque):
        member_map[_norm(m.full_name)] = m

    return inserted, errors, member_map


def _get_or_create_membership_year(mosque, year_int):
    obj, _ = MembershipYear.objects.get_or_create(
        mosque=mosque,
        year=year_int,
        defaults={"amount_expected": Decimal("0"), "is_active": False},
    )
    return obj


def _import_cotisations(mosque, rows, member_map):
    inserted = 0
    errors = []
    membership_year_cache = {}

    try:
        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                nom_adherent = (row.get("nom_adherent") or "").strip()
                date_val     = _parse_date(row.get("date"), i, "cotisations", errors)
                montant      = _parse_amount(row.get("montant"), i, "cotisations", errors)

                if not nom_adherent or date_val is None or montant is None:
                    errors.append({"entite": "cotisations", "ligne": i,
                                   "raison": "Champs obligatoires manquants"})
                    continue

                member = member_map.get(_norm(nom_adherent))
                if not member:
                    errors.append({"entite": "cotisations", "ligne": i,
                                   "raison": f"Adhérent '{nom_adherent}' non trouvé"})
                    continue

                year_int = int(row.get("annee") or date_val.year)
                if year_int not in membership_year_cache:
                    membership_year_cache[year_int] = _get_or_create_membership_year(mosque, year_int)
                membership_year = membership_year_cache[year_int]

                try:
                    existing = MembershipPayment.objects.filter(
                        mosque=mosque,
                        member=member,
                        membership_year=membership_year,
                        date=date_val,
                        amount=montant,
                    ).first()
                    if existing is None:
                        MembershipPayment.objects.create(
                            mosque=mosque,
                            member=member,
                            membership_year=membership_year,
                            date=date_val,
                            amount=montant,
                            method=_parse_method(row.get("mode_paiement")),
                            status=_parse_status(row.get("statut")),
                            note=  (row.get("note") or "").strip(),
                        )
                        inserted += 1
                except Exception as e:
                    errors.append({"entite": "cotisations", "ligne": i,
                                   "raison": str(e)})
    except Exception as e:
        errors.append({"entite": "cotisations", "ligne": 0,
                       "raison": f"Erreur bloc : {e}"})

    return inserted, errors


REGIME_MAP = {
    "1901": "1901", "loi 1901": "1901", "association": "1901",
    "1905": "1905", "loi 1905": "1905", "culte": "1905",
}

DIRECTION_MAP = {
    "recette": "IN",  "in": "IN",  "entrée": "IN",  "entree": "IN",
    "dépense": "OUT", "out": "OUT", "depense": "OUT", "sortie": "OUT",
}

CATEGORY_MAP = {
    "don": "don", "sadaqa": "don", "donation": "don",
    "loyer": "loyer",
    "salaire": "salaire", "honoraires": "salaire",
    "facture": "facture", "charge": "facture", "charges": "facture",
    "ecole": "ecole", "école": "ecole",
    "cotisation": "cotisation",
    "projet": "projet", "travaux": "projet",
    "subvention": "subvention",
}


def _import_transactions(mosque, rows):
    inserted = 0
    errors = []

    # Charger les comptes bancaires une seule fois
    bank_accounts = {_norm(b.regime): b for b in BankAccount.objects.filter(mosque=mosque)}

    try:
        with transaction.atomic():
            for i, row in enumerate(rows, 1):
                date_val = _parse_date(row.get("date"), i, "transactions", errors)
                montant  = _parse_amount(row.get("montant"), i, "transactions", errors)
                libelle  = (row.get("libelle") or "").strip()
                type_val = _norm(row.get("type") or "")

                if date_val is None or montant is None or not libelle or not type_val:
                    errors.append({"entite": "transactions", "ligne": i,
                                   "raison": "Champs obligatoires manquants (date, montant, libelle, type)"})
                    continue

                direction = DIRECTION_MAP.get(type_val)
                if not direction:
                    errors.append({"entite": "transactions", "ligne": i,
                                   "raison": f"Type invalide : '{row.get('type')}' (attendu: recette/dépense)"})
                    continue

                regime_raw = _norm(row.get("regime") or "")
                regime = REGIME_MAP.get(regime_raw, "")

                # Résolution du compte bancaire par régime
                bank_account = bank_accounts.get(regime) or bank_accounts.get("1901")

                categorie_raw = _norm(row.get("categorie") or "")
                categorie = CATEGORY_MAP.get(categorie_raw, "autre")

                try:
                    existing = TreasuryTransaction.objects.filter(
                        mosque=mosque,
                        date=date_val,
                        label=libelle,
                        amount=montant,
                        direction=direction,
                    ).first()
                    if existing is None:
                        TreasuryTransaction.objects.create(
                            mosque=mosque,
                            date=date_val,
                            label=libelle,
                            amount=montant,
                            direction=direction,
                            category=      categorie,
                            method=        _parse_method(row.get("mode_paiement")),
                            regime_fiscal= regime,
                            bank_account=  bank_account,
                            note=          (row.get("note") or "").strip(),
                            source=        "import",
                        )
                        inserted += 1
                except Exception as e:
                    errors.append({"entite": "transactions", "ligne": i,
                                   "raison": str(e)})
    except Exception as e:
        errors.append({"entite": "transactions", "ligne": 0,
                       "raison": f"Erreur bloc : {e}"})

    return inserted, errors


# ─── Vue principale ────────────────────────────────────────────────────────────

class BulkImportView(APIView):
    """
    POST /api/admin/import/bulk
    Body JSON :
    {
        "familles":         [...],
        "enfants":          [...],
        "paiements_ecole":  [...],
        "adherents":        [...],
        "cotisations":      [...],
        "transactions":     [...]
    }
    Chaque liste est optionnelle — envoyer seulement les blocs souhaités.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Vérification admin
        if not (request.user.is_staff or getattr(request.user, "role", None) in ("ADMIN", "SUPERADMIN")):
            return Response({"error": "Réservé aux administrateurs."}, status=403)

        mosque = getattr(request.user, "mosque", None)
        if not mosque:
            return Response({"error": "Aucune mosquée associée à cet utilisateur."}, status=400)

        data = request.data
        all_errors = []
        inserted = {
            "familles": 0, "enfants": 0, "paiements_ecole": 0,
            "adherents": 0, "cotisations": 0, "transactions": 0,
        }

        logger.info("BulkImport démarré — mosque=%s user=%s", mosque.slug, request.user.username)

        # ── 1. Familles ──────────────────────────────────────────────────────
        family_map = {}
        if data.get("familles"):
            n, errs, family_map = _import_familles(mosque, data["familles"])
            inserted["familles"] = n
            all_errors.extend(errs)
            logger.info("BulkImport familles: %d insérées, %d erreurs", n, len(errs))

        # ── 2. Enfants ───────────────────────────────────────────────────────
        child_map = {}
        if data.get("enfants"):
            n, errs, child_map = _import_enfants(mosque, data["enfants"], family_map)
            inserted["enfants"] = n
            all_errors.extend(errs)
            logger.info("BulkImport enfants: %d insérés, %d erreurs", n, len(errs))

        # ── 3. Paiements école ───────────────────────────────────────────────
        if data.get("paiements_ecole"):
            n, errs = _import_paiements_ecole(mosque, data["paiements_ecole"], family_map, child_map)
            inserted["paiements_ecole"] = n
            all_errors.extend(errs)
            logger.info("BulkImport paiements_ecole: %d insérés, %d erreurs", n, len(errs))

        # ── 4. Adhérents ─────────────────────────────────────────────────────
        member_map = {}
        if data.get("adherents"):
            n, errs, member_map = _import_adherents(mosque, data["adherents"])
            inserted["adherents"] = n
            all_errors.extend(errs)
            logger.info("BulkImport adherents: %d insérés, %d erreurs", n, len(errs))

        # ── 5. Cotisations ───────────────────────────────────────────────────
        if data.get("cotisations"):
            n, errs = _import_cotisations(mosque, data["cotisations"], member_map)
            inserted["cotisations"] = n
            all_errors.extend(errs)
            logger.info("BulkImport cotisations: %d insérées, %d erreurs", n, len(errs))

        # ── 6. Transactions ──────────────────────────────────────────────────
        if data.get("transactions"):
            n, errs = _import_transactions(mosque, data["transactions"])
            inserted["transactions"] = n
            all_errors.extend(errs)
            logger.info("BulkImport transactions: %d insérées, %d erreurs", n, len(errs))

        # ── Journal d'audit ──────────────────────────────────────────────────
        try:
            from core.models import AuditLog  # noqa — optionnel
            AuditLog.objects.create(
                mosque=mosque,
                user=request.user,
                action="bulk_import",
                details=f"Import bulk: {inserted} — {len(all_errors)} erreurs",
            )
        except Exception:
            pass  # AuditLog optionnel, ne bloque pas

        total_inserted = sum(inserted.values())
        logger.info("BulkImport terminé — mosque=%s total=%d erreurs=%d",
                    mosque.slug, total_inserted, len(all_errors))

        return Response({
            "success": True,
            "inserted": inserted,
            "errors": all_errors,
        }, status=200)
