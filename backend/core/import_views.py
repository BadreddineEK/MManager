"""
Import en masse — CSV/Excel
============================
Trois endpoints sécurisés (ADMIN uniquement) :

  POST /api/import/transactions/   — transactions_tresorerie.csv  (559 lignes)
  POST /api/import/members/        — adherents_mosquee.csv        (638 lignes)
  POST /api/import/school/         — inscriptions_ecole.csv       (119 lignes)

Comportement :
  1. Lecture + validation ligne par ligne (CSV ou Excel .xlsx)
  2. Rapport d'erreurs sans toucher la base si dry_run=true
  3. Transaction atomique : tout passe ou rien (si dry_run=false)
  4. Réponse JSON : { imported, skipped, errors: [{row, field, message}] }

Colonnes acceptées :
  transactions  → date, objet, montant_entree, montant_sortie, categorie, annee, mois
  membres       → nom_prenom, telephone, email, adresse, mode_paiement, total_paye, [jan..dec]
  école         → nom_parents, prenom_enfant, niveau, total_du, total_verse, [sept..juin],
                  tel_papa, tel_maman, email
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction as db_transaction
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminRole as IsAdmin
from membership.models import Member, MembershipPayment, MembershipYear
from school.models import Child, Family, SchoolPayment, SchoolYear
from treasury.models import TreasuryTransaction

logger = logging.getLogger("core")

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de mapping
# ─────────────────────────────────────────────────────────────────────────────

# Mapping libellé CSV → slug interne TreasuryTransaction.CATEGORY_CHOICES
CATEGORY_MAP: dict[str, str] = {
    "cotisation mosquée": "cotisation",
    "cotisation mosquee": "cotisation",
    "cotisation": "cotisation",
    "don": "don",
    "don / sadaqa": "don",
    "sadaqa": "don",
    "loyer": "loyer",
    "salaire": "salaire",
    "salaire / honoraires": "salaire",
    "honoraires": "salaire",
    "facture": "facture",
    "charges": "facture",
    "facture / charges": "facture",
    "école coranique": "ecole",
    "ecole coranique": "ecole",
    "ecole": "ecole",
    "projet": "projet",
    "travaux": "projet",
    "projet / travaux": "projet",
    "subvention": "subvention",
    "pôle irchad": "autre",
    "pole irchad": "autre",
    "autre": "autre",
    "divers": "autre",
    "": "autre",
}

METHOD_MAP: dict[str, str] = {
    "vir": "virement",
    "virement": "virement",
    "chèq": "cheque",
    "cheq": "cheque",
    "chèque": "cheque",
    "cheque": "cheque",
    "esp": "cash",
    "espèces": "cash",
    "especes": "cash",
    "cash": "cash",
    "cb": "autre",
    "carte": "autre",
    "autre": "autre",
    "": "autre",
}

# Mois scolaires (sept → juin) → numéros de mois
SCHOOL_MONTHS: list[tuple[str, int]] = [
    ("sept", 9), ("oct", 10), ("nov", 11), ("dec", 12),
    ("jan", 1), ("fev", 2), ("mars", 3), ("avr", 4),
    ("mai", 5), ("juin", 6),
]

# Mois civils (jan → dec) → numéros de mois
CIVIL_MONTHS: list[tuple[str, int]] = [
    ("jan", 1), ("fev", 2), ("mars", 3), ("avr", 4),
    ("mai", 5), ("juin", 6), ("juil", 7), ("aout", 8),
    ("sept", 9), ("oct", 10), ("nov", 11), ("dec", 12),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_csv(file_bytes: bytes) -> list[dict[str, str]]:
    """
    Décode le fichier CSV en UTF-8 (avec fallback latin-1) et renvoie
    une liste de dicts dont les clés sont normalisées en minuscules + strip.
    """
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError("Impossible de décoder le fichier (UTF-8 ou Latin-1 requis).")

    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append({k.strip().lower(): v.strip() for k, v in row.items()})
    return rows


def _read_excel(file_bytes: bytes) -> list[dict[str, str]]:
    """Lit un .xlsx avec openpyxl et renvoie la même structure que _read_csv."""
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError as exc:
        raise ValueError("openpyxl est requis pour importer des fichiers .xlsx.") from exc

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip().lower() if h is not None else "" for h in next(rows_iter)]
    result = []
    for row in rows_iter:
        result.append({headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)})
    wb.close()
    return result


def _parse_file(uploaded_file: Any) -> list[dict[str, str]]:
    """Détecte le format et délègue au bon parser."""
    name = (uploaded_file.name or "").lower()
    content = uploaded_file.read()
    if name.endswith(".xlsx"):
        return _read_excel(content)
    return _read_csv(content)


def _parse_decimal(value: str, field: str, row_num: int, errors: list) -> Decimal | None:
    """Convertit une chaîne en Decimal (virgule ou point). Retourne None si vide."""
    value = value.replace(",", ".").replace(" ", "").replace("\xa0", "")
    if not value or value in ("-", "0", "0.0", "0.00"):
        return None
    try:
        d = Decimal(value)
        if d < 0:
            errors.append({"row": row_num, "field": field, "message": f"Montant négatif ignoré : {value}"})
            return None
        return d
    except InvalidOperation:
        errors.append({"row": row_num, "field": field, "message": f"Montant invalide : '{value}'"})
        return None


def _parse_date(value: str, row_num: int, errors: list, fallback_year: int | None = None) -> date | None:
    """
    Essaie plusieurs formats de date courants dans les exports Excel français :
    DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD/MM/YY.
    """
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    if fallback_year and value == "":
        return None
    if value:
        errors.append({"row": row_num, "field": "date", "message": f"Format de date non reconnu : '{value}'"})
    return None


def _normalize_method(raw: str) -> str:
    return METHOD_MAP.get(raw.strip().lower(), "autre")


def _normalize_category(raw: str) -> str:
    return CATEGORY_MAP.get(raw.strip().lower(), "autre")


# ─────────────────────────────────────────────────────────────────────────────
# Vue 1 — Import transactions trésorerie
# ─────────────────────────────────────────────────────────────────────────────

class ImportTransactionsView(APIView):
    """
    POST /api/import/transactions/

    Form-data :
      file      — fichier CSV ou Excel
      mosque_id — ID de la mosquée cible (int)
      dry_run   — "true" pour simuler sans écrire (défaut : false)
      year      — filtrer sur une année uniquement (optionnel)

    Colonnes CSV attendues :
      date, objet, montant_entree, montant_sortie, categorie
      (annee et mois sont optionnels — ignorés si date est présente)
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        mosque, dry_run, error_resp = _extract_common_params(request)
        if error_resp:
            return error_resp

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Champ 'file' manquant."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = _parse_file(uploaded)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        errors: list[dict] = []
        to_create: list[TreasuryTransaction] = []
        skipped = 0

        for i, row in enumerate(rows, start=2):  # ligne 1 = en-tête
            # Date
            raw_date = row.get("date", "")
            parsed_date = _parse_date(raw_date, i, errors)
            if parsed_date is None:
                # Tenter de reconstruire depuis annee + mois
                raw_year = row.get("annee", "").strip()
                raw_month = row.get("mois", "").strip()
                if raw_year.isdigit() and raw_month.isdigit():
                    try:
                        parsed_date = date(int(raw_year), int(raw_month), 1)
                    except ValueError:
                        errors.append({"row": i, "field": "date", "message": "annee/mois invalides"})
                        skipped += 1
                        continue
                else:
                    skipped += 1
                    continue

            # Montants
            entree = _parse_decimal(row.get("montant_entree", ""), "montant_entree", i, errors)
            sortie = _parse_decimal(row.get("montant_sortie", ""), "montant_sortie", i, errors)

            if entree is None and sortie is None:
                skipped += 1
                continue  # ligne vide ou séparateur

            direction = TreasuryTransaction.DIRECTION_IN if entree else TreasuryTransaction.DIRECTION_OUT
            amount = entree if entree else sortie

            label = row.get("objet", "").strip() or "Import CSV"
            category = _normalize_category(row.get("categorie", ""))

            to_create.append(TreasuryTransaction(
                mosque=mosque,
                date=parsed_date,
                label=label,
                direction=direction,
                amount=amount,
                category=category,
                method="virement",  # relevé bancaire → virement par défaut
                note="Import CSV",
            ))

        return _finalize_import(to_create, errors, skipped, dry_run, "transactions", request.user)


# ─────────────────────────────────────────────────────────────────────────────
# Vue 2 — Import adhérents
# ─────────────────────────────────────────────────────────────────────────────

class ImportMembersView(APIView):
    """
    POST /api/import/members/

    Form-data :
      file            — CSV ou Excel
      mosque_id       — int
      dry_run         — true/false
      membership_year — ID de l'année de cotisation cible (int)

    Colonnes CSV attendues :
      nom_prenom, telephone, email, adresse, mode_paiement, total_paye,
      jan, fev, mars, avr, mai, juin, juil, aout, sept, oct, nov, dec

    Logique :
      - Crée le Member si inexistant (match sur full_name + mosque)
      - Crée un MembershipPayment par mois où un montant > 0 est trouvé
      - Si total_paye > 0 et aucun mois renseigné → un seul paiement global
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        mosque, dry_run, error_resp = _extract_common_params(request)
        if error_resp:
            return error_resp

        year_id = request.data.get("membership_year")
        if not year_id:
            return Response({"detail": "Champ 'membership_year' (ID) requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            m_year = MembershipYear.objects.get(pk=int(year_id), mosque=mosque)
        except (MembershipYear.DoesNotExist, ValueError):
            return Response({"detail": "Année de cotisation introuvable pour cette mosquée."}, status=status.HTTP_404_NOT_FOUND)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Champ 'file' manquant."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = _parse_file(uploaded)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        errors: list[dict] = []
        members_to_create: list[Member] = []
        payments_to_create: list[MembershipPayment] = []
        skipped = 0

        # Cache des noms déjà en base pour éviter les doublons
        existing_names: set[str] = set(
            Member.objects.filter(mosque=mosque).values_list("full_name", flat=True)
        )
        # Noms déjà ajoutés dans ce batch
        batch_names: set[str] = set()

        for i, row in enumerate(rows, start=2):
            full_name = row.get("nom_prenom", "").strip()
            if not full_name:
                skipped += 1
                continue

            phone = row.get("telephone", "").strip() or row.get("tel", "").strip() or ""
            email = row.get("email", "").strip()
            address = row.get("adresse", "").strip()
            method = _normalize_method(row.get("mode_paiement", ""))

            # Déterminer si le membre doit être créé
            is_new = (full_name not in existing_names) and (full_name not in batch_names)
            if is_new:
                members_to_create.append(Member(
                    mosque=mosque,
                    full_name=full_name,
                    phone=phone,
                    email=email,
                    address=address,
                ))
                batch_names.add(full_name)

            # Paiements mensuels
            monthly_total = Decimal("0")
            for col, month_num in CIVIL_MONTHS:
                val = _parse_decimal(row.get(col, ""), col, i, errors)
                if val and val > 0:
                    monthly_total += val
                    payments_to_create.append(_pending_membership_payment(
                        mosque=mosque,
                        year=m_year,
                        full_name=full_name,
                        amount=val,
                        month_num=month_num,
                        year_num=m_year.year,
                        method=method,
                    ))

            # Fallback : total_paye si aucun mois détaillé
            if monthly_total == 0:
                total = _parse_decimal(row.get("total_paye", ""), "total_paye", i, errors)
                if total and total > 0:
                    payments_to_create.append(_pending_membership_payment(
                        mosque=mosque,
                        year=m_year,
                        full_name=full_name,
                        amount=total,
                        month_num=1,
                        year_num=m_year.year,
                        method=method,
                    ))

        return _finalize_members_import(
            mosque, members_to_create, payments_to_create,
            errors, skipped, dry_run, request.user
        )


def _pending_membership_payment(
    *, mosque, year, full_name: str,
    amount: Decimal, month_num: int, year_num: int, method: str
) -> dict:
    """Retourne un dict 'en attente' — résolu après bulk_create des membres."""
    return {
        "mosque": mosque,
        "year": year,
        "full_name": full_name,
        "amount": amount,
        "date": date(year_num, month_num, 1),
        "method": method,
    }


def _finalize_members_import(
    mosque, members_to_create, payments_to_create,
    errors, skipped, dry_run, user
) -> Response:
    """Crée les membres puis résout les paiements avec les IDs réels."""
    if dry_run:
        return Response({
            "dry_run": True,
            "would_create": {"members": len(members_to_create), "payments": len(payments_to_create)},
            "skipped": skipped,
            "errors": errors,
        })

    imported_members = 0
    imported_payments = 0

    try:
        with db_transaction.atomic():
            if members_to_create:
                Member.objects.bulk_create(members_to_create, ignore_conflicts=True)
                imported_members = len(members_to_create)

            # Recharger le mapping nom → id
            name_to_id: dict[str, int] = {
                m.full_name: m.id
                for m in Member.objects.filter(mosque=mosque)
            }

            real_payments: list[MembershipPayment] = []
            for p in payments_to_create:
                member_id = name_to_id.get(p["full_name"])
                if member_id is None:
                    errors.append({"row": "-", "field": "nom_prenom", "message": f"Membre introuvable après import : {p['full_name']}"})
                    continue
                real_payments.append(MembershipPayment(
                    mosque=p["mosque"],
                    membership_year=p["year"],
                    member_id=member_id,
                    amount=p["amount"],
                    date=p["date"],
                    method=p["method"],
                    note="Import CSV",
                ))

            if real_payments:
                MembershipPayment.objects.bulk_create(real_payments, ignore_conflicts=False)
                imported_payments = len(real_payments)

    except Exception as exc:
        logger.exception("Erreur import adhérents")
        return Response({"detail": f"Erreur lors de l'import : {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.info("IMPORT membres: %d membres, %d paiements par %s", imported_members, imported_payments, user)
    return Response({
        "imported": {"members": imported_members, "payments": imported_payments},
        "skipped": skipped,
        "errors": errors,
    }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Vue 3 — Import inscriptions école
# ─────────────────────────────────────────────────────────────────────────────

class ImportSchoolView(APIView):
    """
    POST /api/import/school/

    Form-data :
      file        — CSV ou Excel
      mosque_id   — int
      dry_run     — true/false
      school_year — ID de l'année scolaire cible (int)

    Colonnes CSV attendues :
      nom_parents, prenom_enfant, niveau, total_du, total_verse,
      sept, oct, nov, dec, jan, fev, mars, avr, mai, juin,
      tel_papa, tel_maman, email

    Logique :
      - Crée la Family si inexistante (match nom_parents + mosque)
      - Crée le Child (prenom_enfant + niveau)
      - Crée un SchoolPayment par mois où un montant > 0 est trouvé
      - Si aucun mois → fallback total_verse en paiement unique
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        mosque, dry_run, error_resp = _extract_common_params(request)
        if error_resp:
            return error_resp

        year_id = request.data.get("school_year")
        if not year_id:
            return Response({"detail": "Champ 'school_year' (ID) requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            s_year = SchoolYear.objects.get(pk=int(year_id), mosque=mosque)
        except (SchoolYear.DoesNotExist, ValueError):
            return Response({"detail": "Année scolaire introuvable pour cette mosquée."}, status=status.HTTP_404_NOT_FOUND)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Champ 'file' manquant."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rows = _parse_file(uploaded)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        errors: list[dict] = []
        families_to_create: list[Family] = []
        children_to_create: list[dict] = []   # dict car dépend de l'ID famille
        payments_to_create: list[dict] = []
        skipped = 0

        existing_families: set[str] = set(
            Family.objects.filter(mosque=mosque).values_list("primary_contact_name", flat=True)
        )
        batch_families: set[str] = set()

        for i, row in enumerate(rows, start=2):
            nom_parents = row.get("nom_parents", "").strip()
            prenom_enfant = row.get("prenom_enfant", "").strip()

            if not nom_parents:
                skipped += 1
                continue

            phone1 = row.get("tel_papa", "").strip() or ""
            phone2 = row.get("tel_maman", "").strip() or ""
            email = row.get("email", "").strip()
            niveau = row.get("niveau", "").strip().upper() or "N1"

            is_new = (nom_parents not in existing_families) and (nom_parents not in batch_families)
            if is_new:
                families_to_create.append(Family(
                    mosque=mosque,
                    primary_contact_name=nom_parents,
                    phone1=phone1,
                    phone2=phone2,
                    email=email,
                ))
                batch_families.add(nom_parents)

            # Toujours créer l'enfant (même famille, plusieurs enfants possibles)
            children_to_create.append({
                "family_name": nom_parents,
                "first_name": prenom_enfant or "Enfant",
                "level": niveau,
            })

            # Paiements mensuels scolaires
            monthly_total = Decimal("0")
            for col, month_num in SCHOOL_MONTHS:
                val = _parse_decimal(row.get(col, ""), col, i, errors)
                if val and val > 0:
                    monthly_total += val
                    year_num = s_year.start_date.year if month_num >= 9 else s_year.end_date.year
                    payments_to_create.append({
                        "family_name": nom_parents,
                        "child_first": prenom_enfant or "Enfant",
                        "amount": val,
                        "date": date(year_num, month_num, 1),
                        "method": "cash",
                    })

            # Fallback total_verse
            if monthly_total == 0:
                total = _parse_decimal(row.get("total_verse", ""), "total_verse", i, errors)
                if total and total > 0:
                    payments_to_create.append({
                        "family_name": nom_parents,
                        "child_first": prenom_enfant or "Enfant",
                        "amount": total,
                        "date": s_year.start_date,
                        "method": "cash",
                    })

        return _finalize_school_import(
            mosque, s_year,
            families_to_create, children_to_create, payments_to_create,
            errors, skipped, dry_run, request.user
        )


def _finalize_school_import(
    mosque, s_year,
    families_to_create, children_to_create, payments_to_create,
    errors, skipped, dry_run, user
) -> Response:
    if dry_run:
        return Response({
            "dry_run": True,
            "would_create": {
                "families": len(families_to_create),
                "children": len(children_to_create),
                "payments": len(payments_to_create),
            },
            "skipped": skipped,
            "errors": errors,
        })

    imported = {"families": 0, "children": 0, "payments": 0}

    try:
        with db_transaction.atomic():
            if families_to_create:
                Family.objects.bulk_create(families_to_create, ignore_conflicts=True)
                imported["families"] = len(families_to_create)

            name_to_family: dict[str, Family] = {
                f.primary_contact_name: f
                for f in Family.objects.filter(mosque=mosque)
            }

            real_children: list[Child] = []
            for c in children_to_create:
                fam = name_to_family.get(c["family_name"])
                if fam is None:
                    errors.append({"row": "-", "field": "nom_parents", "message": f"Famille introuvable : {c['family_name']}"})
                    continue
                real_children.append(Child(
                    mosque=mosque,
                    family=fam,
                    first_name=c["first_name"],
                    level=c["level"],
                ))

            if real_children:
                Child.objects.bulk_create(real_children, ignore_conflicts=False)
                imported["children"] = len(real_children)

            # Mapping (family_name, child_first) → Child id
            child_map: dict[tuple[str, str], Child] = {}
            for ch in Child.objects.filter(mosque=mosque).select_related("family"):
                key = (ch.family.primary_contact_name, ch.first_name)
                child_map[key] = ch

            real_payments: list[SchoolPayment] = []
            for p in payments_to_create:
                fam = name_to_family.get(p["family_name"])
                if fam is None:
                    continue
                child = child_map.get((p["family_name"], p["child_first"]))
                real_payments.append(SchoolPayment(
                    mosque=mosque,
                    school_year=s_year,
                    family=fam,
                    child=child,
                    amount=p["amount"],
                    date=p["date"],
                    method=p["method"],
                    note="Import CSV",
                ))

            if real_payments:
                SchoolPayment.objects.bulk_create(real_payments, ignore_conflicts=False)
                imported["payments"] = len(real_payments)

    except Exception as exc:
        logger.exception("Erreur import école")
        return Response({"detail": f"Erreur lors de l'import : {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.info("IMPORT école: %s par %s", imported, user)
    return Response({"imported": imported, "skipped": skipped, "errors": errors}, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers communs
# ─────────────────────────────────────────────────────────────────────────────

def _extract_common_params(request: Request):
    """
    Extrait et valide mosque_id + dry_run depuis la requête.
    Retourne (mosque, dry_run, None) ou (None, None, Response d'erreur).
    """
    from core.models import Mosque  # import local pour éviter les cycles

    mosque_id = request.data.get("mosque_id")
    if not mosque_id:
        return None, None, Response(
            {"detail": "Champ 'mosque_id' requis."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        mosque = Mosque.objects.get(pk=int(mosque_id))
    except (Mosque.DoesNotExist, ValueError):
        return None, None, Response(
            {"detail": "Mosquée introuvable."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Vérifier que l'utilisateur appartient à cette mosquée (sauf superuser)
    if not request.user.is_superuser and request.user.mosque_id != mosque.id:
        return None, None, Response(
            {"detail": "Vous n'avez pas accès à cette mosquée."},
            status=status.HTTP_403_FORBIDDEN,
        )

    dry_run = str(request.data.get("dry_run", "false")).lower() == "true"
    return mosque, dry_run, None


def _finalize_import(
    to_create: list,
    errors: list,
    skipped: int,
    dry_run: bool,
    label: str,
    user,
) -> Response:
    """Commit ou dry-run pour les imports sans dépendances (ex: transactions)."""
    if dry_run:
        return Response({
            "dry_run": True,
            "would_create": len(to_create),
            "skipped": skipped,
            "errors": errors,
        })

    if not to_create:
        return Response({
            "imported": 0,
            "skipped": skipped,
            "errors": errors,
            "detail": "Aucune ligne valide à importer.",
        }, status=status.HTTP_200_OK)

    try:
        with db_transaction.atomic():
            model_class = to_create[0].__class__
            model_class.objects.bulk_create(to_create)
    except Exception as exc:
        logger.exception("Erreur import %s", label)
        return Response({"detail": f"Erreur lors de l'import : {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.info("IMPORT %s: %d lignes importées par %s", label, len(to_create), user)
    return Response({
        "imported": len(to_create),
        "skipped": skipped,
        "errors": errors,
    }, status=status.HTTP_201_CREATED)
