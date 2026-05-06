"""
Import bancaire configurable — Power Query style
=================================================
POST /api/import/bank/preview/   — analyse le CSV, retourne colonnes détectées + aperçu
POST /api/import/bank/           — import réel avec un profil existant ou un mapping ad-hoc

Le mapping peut être :
  A) profile_id (int)           → utilise un BankImportProfile existant
  B) mapping JSON inline        → utilisé une fois, non sauvegardé
  C) mapping JSON + save=true   → sauvegardé comme nouveau BankImportProfile

Format du mapping inline (reprend les champs de BankImportProfile) :
  {
    "separator":        ";",
    "encoding":         "utf-8-sig",
    "date_format":      "%d/%m/%Y",
    "decimal_sep":      ",",
    "skip_rows":        0,
    "date_column":      "Date comptable",
    "label_column":     "Libelle simplifie",
    "detail_column":    "Informations complementaires",
    "debit_column":     "Debit",
    "credit_column":    "Credit",
    "type_column":      "Type operation",
    "reference_column": "Reference"
  }
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

from core.models import BankImportProfile, Staff
from core.permissions import HasMosquePermission, IsAdminRole as IsAdmin
from core.utils import get_mosque, log_action
from treasury.models import TreasuryTransaction

logger = logging.getLogger("core")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _decode_file(content: bytes, encoding: str = "utf-8-sig") -> str:
    for enc in (encoding, "utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError("Impossible de décoder le fichier. Essayez UTF-8 ou Latin-1.")


def _parse_bank_csv(content: bytes, profile: dict) -> tuple[list[str], list[dict]]:
    """
    Lit le CSV avec le séparateur et encodage du profil.
    Retourne (headers, rows) où rows est une liste de dicts clé=valeur brute.
    """
    sep = profile.get("separator", ";")
    enc = profile.get("encoding", "utf-8-sig")
    skip = int(profile.get("skip_rows", 0))

    text = _decode_file(content, enc)
    lines = text.splitlines()
    # Ignorer les lignes de skip
    text = "\n".join(lines[skip:])

    reader = csv.DictReader(io.StringIO(text), delimiter=sep)
    headers = reader.fieldnames or []
    rows = [dict(row) for row in reader]
    return list(headers), rows


def _parse_amount(value: str, decimal_sep: str = ",") -> Decimal | None:
    """Convertit un montant string → Decimal. Retourne None si vide/nul."""
    if not value:
        return None
    value = value.strip().replace(" ", "").replace("\xa0", "")
    if decimal_sep == ",":
        value = value.replace(",", ".")
    try:
        d = Decimal(value)
        # On prend la valeur absolue — la direction est déterminée par la colonne
        return abs(d) if d != 0 else None
    except InvalidOperation:
        return None


def _parse_date(value: str, date_format: str = "%d/%m/%Y") -> date | None:
    value = value.strip() if value else ""
    if not value:
        return None
    # Essayer le format configuré d'abord, puis fallbacks
    for fmt in (date_format, "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _auto_categorize(label: str, detail: str, type_op: str) -> str:
    """
    Catégorisation automatique basée sur le libellé + type opération bancaire.
    Les mots-clés sont simples et extensibles — la mosquée peut toujours corriger inline.
    """
    text = (label + " " + detail).lower()
    type_op = (type_op or "").lower()

    if any(k in text for k in ("salaire", "versement salaire", "remun")):
        return "salaire"
    if any(k in text for k in ("urssaf", "cotis soc", "cotisation soc")):
        return "facture"
    if any(k in text for k in ("edf", "gaz", "elec", "eau", "sogedo", "engie")):
        return "facture"
    if any(k in text for k in ("free telecom", "sfr", "orange", "bouygues", "téléphone")):
        return "facture"
    if any(k in text for k in ("loyer", "bail", "location")):
        return "loyer"
    if any(k in text for k in ("allianz", "assur", "maif")):
        return "facture"
    if any(k in text for k in ("ecole", "école", "cours", "scolarit", "inscription")):
        return "ecole"
    if any(k in text for k in ("cotis", "adhes", "adhér")):
        return "cotisation"
    if any(k in text for k in ("helloasso", "don", "sadaqa", "zakat", "mosque", "mosquée")):
        return "don"
    if any(k in text for k in ("travaux", "reparation", "réparation", "materiel", "achat")):
        return "projet"
    if any(k in text for k in ("subvention", "subv")):
        return "subvention"
    if "prelevement" in type_op or "frais" in type_op:
        return "facture"
    return "autre"


def _match_staff(label: str, detail: str, staff_list: list) -> Any | None:
    """Retourne le Staff dont le name_keyword est trouvé dans le libellé."""
    text = (label + " " + detail).lower()
    for staff in staff_list:
        keyword = (staff.name_keyword or "").strip().lower()
        if keyword and keyword in text:
            return staff
    return None


def _profile_from_request(request_data: dict, mosque_id: int = None) -> dict:
    """
    Résout le profil de mapping depuis :
      1. profile_id → charge le BankImportProfile en base
      2. mapping inline JSON dans request_data
    Retourne un dict normalisé.
    """
    profile_id = request_data.get("profile_id")
    if profile_id:
        try:
            bp = BankImportProfile.objects.get(id=profile_id)
            return {
                "separator":        bp.separator,
                "encoding":         bp.encoding,
                "date_format":      bp.date_format,
                "decimal_sep":      bp.decimal_sep,
                "skip_rows":        bp.skip_rows,
                "date_column":      bp.date_column,
                "label_column":     bp.label_column,
                "detail_column":    bp.detail_column,
                "debit_column":     bp.debit_column,
                "credit_column":    bp.credit_column,
                "amount_column":    bp.amount_column,
                "type_column":      bp.type_column,
                "reference_column": bp.reference_column,
                "_profile_obj":     bp,
            }
        except BankImportProfile.DoesNotExist:
            raise ValueError(f"Profil d'import {profile_id} introuvable.")

    # Mapping inline — valeurs par défaut si absent
    return {
        "separator":        request_data.get("separator", ";"),
        "encoding":         request_data.get("encoding", "utf-8-sig"),
        "date_format":      request_data.get("date_format", "%d/%m/%Y"),
        "decimal_sep":      request_data.get("decimal_sep", ","),
        "skip_rows":        int(request_data.get("skip_rows", 0)),
        "date_column":      request_data.get("date_column", "date"),
        "label_column":     request_data.get("label_column", "libelle"),
        "detail_column":    request_data.get("detail_column", ""),
        "debit_column":     request_data.get("debit_column", ""),
        "credit_column":    request_data.get("credit_column", ""),
        "amount_column":    request_data.get("amount_column", ""),
        "type_column":      request_data.get("type_column", ""),
        "reference_column": request_data.get("reference_column", ""),
        "_profile_obj":     None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Vue 1 — Prévisualisation CSV (analyse sans écriture)
# ─────────────────────────────────────────────────────────────────────────────

class BankImportPreviewView(APIView):
    """
    POST /api/import/bank/preview/

    Form-data :
      file        — fichier CSV
      separator   — optionnel (défaut ";")
      encoding    — optionnel (défaut "utf-8-sig")
      skip_rows   — optionnel (défaut 0)

    Retourne :
      columns     — liste des colonnes détectées
      preview     — 5 premières lignes brutes
      profiles    — profils sauvegardés pour cette mosquée
    """
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Mosquée introuvable."}, status=status.HTTP_400_BAD_REQUEST)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Champ 'file' manquant."}, status=status.HTTP_400_BAD_REQUEST)

        content = uploaded.read()
        profile = _profile_from_request(request.data)

        try:
            headers, rows = _parse_bank_csv(content, profile)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Profils sauvegardés pour cette mosquée
        saved_profiles = list(
            BankImportProfile.objects.filter(mosque=mosque).values(
                "id", "label", "is_default",
                "date_column", "label_column", "debit_column", "credit_column",
            )
        )

        return Response({
            "columns": headers,
            "preview": rows[:5],
            "total_rows": len(rows),
            "saved_profiles": saved_profiles,
        })


# ─────────────────────────────────────────────────────────────────────────────
# Vue 2 — Import réel
# ─────────────────────────────────────────────────────────────────────────────

class BankImportView(APIView):
    """
    POST /api/import/bank/

    Form-data :
      file          — fichier CSV
      mosque_id     — ID mosquée (int)
      dry_run       — "true" pour simuler (défaut: false)
      bank_account_id — ID du compte bancaire (optionnel)
      save_profile  — "true" pour sauvegarder le mapping comme profil
      profile_label — nom du profil à sauvegarder

      + tous les champs de mapping (voir _profile_from_request)
        OU profile_id pour utiliser un profil existant
    """
    permission_classes = [IsAuthenticated, HasMosquePermission, IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request: Request) -> Response:
        mosque = get_mosque(request)
        if mosque is None:
            return Response({"detail": "Mosquée introuvable."}, status=status.HTTP_400_BAD_REQUEST)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Champ 'file' manquant."}, status=status.HTTP_400_BAD_REQUEST)

        dry_run = str(request.data.get("dry_run", "false")).lower() == "true"
        bank_account_id = request.data.get("bank_account_id")

        try:
            profile = _profile_from_request(request.data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        content = uploaded.read()
        try:
            _, rows = _parse_bank_csv(content, profile)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Charger le personnel actif pour le matching automatique
        staff_list = list(Staff.objects.filter(mosque=mosque, is_active=True))

        # Colonnes
        date_col      = profile["date_column"]
        label_col     = profile["label_column"]
        detail_col    = profile.get("detail_column", "")
        debit_col     = profile.get("debit_column", "")
        credit_col    = profile.get("credit_column", "")
        amount_col    = profile.get("amount_column", "")
        type_col      = profile.get("type_column", "")
        ref_col       = profile.get("reference_column", "")
        dec_sep       = profile.get("decimal_sep", ",")
        date_fmt      = profile.get("date_format", "%d/%m/%Y")

        errors: list[dict] = []
        to_create: list[TreasuryTransaction] = []
        skipped = 0

        for i, row in enumerate(rows, start=2):
            # Date
            raw_date = row.get(date_col, "").strip()
            parsed_date = _parse_date(raw_date, date_fmt)
            if parsed_date is None:
                if raw_date:
                    errors.append({"row": i, "field": "date", "message": f"Date non reconnue : '{raw_date}'"})
                skipped += 1
                continue

            # Libellé
            label = row.get(label_col, "").strip()
            detail = row.get(detail_col, "").strip() if detail_col else ""
            full_label = f"{label} — {detail}".strip(" —") if detail else label
            if not full_label:
                full_label = "Import bancaire"

            # Type opération
            type_op = row.get(type_col, "").strip() if type_col else ""

            # Montants
            if debit_col and credit_col:
                debit_val  = _parse_amount(row.get(debit_col, ""), dec_sep)
                credit_val = _parse_amount(row.get(credit_col, ""), dec_sep)
                if debit_val is None and credit_val is None:
                    skipped += 1
                    continue
                if credit_val:
                    direction = TreasuryTransaction.DIRECTION_IN
                    amount = credit_val
                else:
                    direction = TreasuryTransaction.DIRECTION_OUT
                    amount = debit_val
            elif amount_col:
                raw_amount = row.get(amount_col, "").strip()
                # Montant avec signe
                sign = 1
                if raw_amount.startswith("-"):
                    sign = -1
                    raw_amount = raw_amount[1:]
                parsed = _parse_amount(raw_amount, dec_sep)
                if parsed is None:
                    skipped += 1
                    continue
                amount = parsed
                direction = TreasuryTransaction.DIRECTION_IN if sign > 0 else TreasuryTransaction.DIRECTION_OUT
            else:
                errors.append({"row": i, "field": "montant", "message": "Aucune colonne de montant configurée."})
                skipped += 1
                continue

            # Référence opération (anti-doublon)
            ref = row.get(ref_col, "").strip() if ref_col else ""
            import_op_id = f"{parsed_date.isoformat()}_{ref}_{amount}" if ref else None

            # Vérifier doublon si on a une référence
            if import_op_id and TreasuryTransaction.objects.filter(
                mosque=mosque,
                import_operation_id=import_op_id,
            ).exists():
                skipped += 1
                continue

            # Catégorie automatique
            category = _auto_categorize(label, detail, type_op)

            # Matching personnel
            matched_staff = _match_staff(label, detail, staff_list)

            # Méthode de paiement selon type opération
            method_map = {
                "virement": "virement",
                "remise virement": "virement",
                "remise cheque": "cheque",
                "prelevement sdd": "virement",
                "paiement cb": "autre",
                "remise cb": "autre",
                "frais et extournes": "autre",
            }
            method = method_map.get(type_op.lower(), "virement")

            to_create.append(TreasuryTransaction(
                mosque=mosque,
                date=parsed_date,
                label=full_label,
                direction=direction,
                amount=amount,
                category=category,
                method=method,
                source="import",
                import_operation_id=import_op_id,
                import_status="validated",
                staff=matched_staff,
                note=f"Import bancaire — {type_op}" if type_op else "Import bancaire",
            ))

        if dry_run or errors:
            return Response({
                "dry_run": dry_run,
                "would_import": len(to_create),
                "skipped": skipped,
                "errors": errors[:50],
            })

        # Sauvegarde du profil si demandé
        if str(request.data.get("save_profile", "false")).lower() == "true":
            profile_label = request.data.get("profile_label", "Profil importé")
            if not profile.get("_profile_obj"):
                BankImportProfile.objects.create(
                    mosque=mosque,
                    label=profile_label,
                    separator=profile["separator"],
                    encoding=profile["encoding"],
                    date_format=profile["date_format"],
                    decimal_sep=profile["decimal_sep"],
                    skip_rows=profile["skip_rows"],
                    date_column=profile["date_column"],
                    label_column=profile["label_column"],
                    detail_column=profile.get("detail_column", ""),
                    debit_column=profile.get("debit_column", ""),
                    credit_column=profile.get("credit_column", ""),
                    amount_column=profile.get("amount_column", ""),
                    type_column=profile.get("type_column", ""),
                    reference_column=profile.get("reference_column", ""),
                )

        with db_transaction.atomic():
            created = TreasuryTransaction.objects.bulk_create(to_create, ignore_conflicts=False)

        log_action(request, "IMPORT", "TreasuryTransaction", 0, {
            "source": "bank_csv",
            "imported": len(created),
            "skipped": skipped,
        })

        return Response({
            "imported": len(created),
            "skipped": skipped,
            "errors": errors[:50],
        })


# ─────────────────────────────────────────────────────────────────────────────
# Vue 3 — CRUD profils d'import
# ─────────────────────────────────────────────────────────────────────────────

from rest_framework import serializers as drf_serializers
from rest_framework import viewsets as drf_viewsets


class BankImportProfileSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = BankImportProfile
        exclude = ["mosque"]


class BankImportProfileViewSet(drf_viewsets.ModelViewSet):
    """CRUD profils d'import bancaire."""
    serializer_class = BankImportProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        mosque = get_mosque(self.request)
        if mosque is None:
            return BankImportProfile.objects.none()
        return BankImportProfile.objects.filter(mosque=mosque)

    def perform_create(self, serializer):
        mosque = get_mosque(self.request)
        # Un seul profil default à la fois
        if serializer.validated_data.get("is_default"):
            BankImportProfile.objects.filter(mosque=mosque, is_default=True).update(is_default=False)
        serializer.save(mosque=mosque)

    def perform_update(self, serializer):
        mosque = get_mosque(self.request)
        if serializer.validated_data.get("is_default"):
            BankImportProfile.objects.filter(mosque=mosque, is_default=True).exclude(
                pk=self.get_object().pk
            ).update(is_default=False)
        serializer.save()
