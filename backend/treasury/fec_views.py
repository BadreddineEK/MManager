"""
fec_views.py — Export FEC (Fichier d'Écritures Comptables)
===========================================================
GET /api/treasury/export/fec/?year=2026

Format légal français — Art. A.47 A-1 du LPF
18 colonnes obligatoires, séparées par tabulation, encodage UTF-8 BOM.

Plan comptable simplifié pour associations :
  7xxx  Produits (IN) — dons, cotisations, école, subventions...
  6xxx  Charges (OUT) — loyer, salaire, factures...
  512   Banque
  530   Caisse
"""
import io
import csv
import logging
from datetime import date

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from core.permissions import HasMosquePermission
from core.plan_enforcement import plan_module_permission
from core.utils import get_mosque
from .models import TreasuryTransaction

logger = logging.getLogger("treasury")

# ─────────────────────────────────────────────────────────────────────────────
# Plan comptable simplifié
# ─────────────────────────────────────────────────────────────────────────────

# Comptes de contrepartie (débit/crédit selon direction)
CATEGORY_ACCOUNT = {
    # Produits (7xxx)
    "don":         ("754", "Dons manuels"),
    "cotisation":  ("756", "Cotisations"),
    "ecole":       ("706", "Prestations école"),
    "subvention":  ("748", "Subventions d'exploitation"),
    "loyer":       ("752", "Revenus locatifs"),
    "autre":       ("758", "Autres produits"),
    # Charges (6xxx)
    "salaire":     ("641", "Rémunérations du personnel"),
    "facture":     ("606", "Achats non stockés"),
    "projet":      ("615", "Entretien et réparations"),
}

METHOD_ACCOUNT = {
    "cash":     ("530", "Caisse"),
    "cheque":   ("512", "Banque"),
    "virement": ("512", "Banque"),
    "autre":    ("512", "Banque"),
}

JOURNAL_CODE = {
    "cash":     "CA",   # Caisse
    "cheque":   "BQ",   # Banque
    "virement": "BQ",
    "autre":    "OD",   # Opérations diverses
}

FEC_HEADERS = [
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
]


def _fmt_date(d) -> str:
    """YYYYMMDD"""
    if isinstance(d, str):
        return d.replace("-", "")
    return d.strftime("%Y%m%d")


def _fmt_amount(amount) -> str:
    """Montant avec virgule décimale (norme FEC)."""
    return str(amount).replace(".", ",")


def _get_accounts(tx: TreasuryTransaction):
    """
    Retourne (compte_tiers_num, compte_tiers_lib, compte_treso_num, compte_treso_lib).
    IN  → débit tréso  / crédit produit
    OUT → débit charge / crédit tréso
    """
    cat = tx.category or "autre"
    method = tx.method or "cash"

    tiers_num, tiers_lib = CATEGORY_ACCOUNT.get(cat, ("758", "Autres produits/charges"))
    treso_num, treso_lib = METHOD_ACCOUNT.get(method, ("512", "Banque"))

    # Pour les charges (OUT), adapter le compte (6xxx au lieu de 7xxx)
    if tx.direction == "OUT":
        charge_map = {
            "don": ("658", "Charges diverses"),
            "cotisation": ("658", "Charges diverses"),
            "ecole": ("606", "Charges école"),
            "subvention": ("658", "Charges diverses"),
            "loyer": ("613", "Locations"),
            "autre": ("658", "Charges diverses"),
        }
        if cat in charge_map:
            tiers_num, tiers_lib = charge_map[cat]

    return tiers_num, tiers_lib, treso_num, treso_lib


class FECExportView(APIView):
    """
    GET /api/treasury/export/fec/?year=2026
    Retourne un fichier .txt FEC téléchargeable.

    Paramètres :
      year  (obligatoire) : année fiscale (ex: 2026)
      month (optionnel)   : mois 1-12 pour un export mensuel
    """
    permission_classes = [IsAuthenticated, HasMosquePermission, plan_module_permission("treasury_fec")]

    def get(self, request):
        mosque = get_mosque(request)
        if mosque is None:
            from rest_framework.response import Response
            return Response({"error": "Mosquée introuvable."}, status=400)

        year_param = request.query_params.get("year")
        month_param = request.query_params.get("month")

        if not year_param:
            from rest_framework.response import Response
            return Response({"error": "Paramètre 'year' obligatoire (ex: ?year=2026)."}, status=400)

        try:
            year = int(year_param)
        except ValueError:
            from rest_framework.response import Response
            return Response({"error": "Paramètre 'year' invalide."}, status=400)

        # Filtrer les transactions
        qs = TreasuryTransaction.objects.filter(
            mosque=mosque,
            date__year=year,
        ).order_by("date", "id")

        if month_param:
            try:
                qs = qs.filter(date__month=int(month_param))
            except ValueError:
                pass

        # Exclure les imports en attente
        qs = qs.exclude(import_status="pending")

        transactions = list(qs)

        if not transactions:
            from rest_framework.response import Response
            return Response(
                {"error": f"Aucune transaction validée pour {year}."},
                status=404,
            )

        # ── Génération du fichier FEC ─────────────────────────────────────
        output = io.StringIO()
        writer = csv.writer(output, delimiter="\t", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(FEC_HEADERS)

        for idx, tx in enumerate(transactions, start=1):
            ecriture_num = f"{year}{idx:06d}"
            ecriture_date = _fmt_date(tx.date)
            piece_ref = f"TX{tx.id:08d}"
            piece_date = ecriture_date
            ecriture_lib = (tx.label or "")[:100]
            montant = _fmt_amount(tx.amount)
            journal_code = JOURNAL_CODE.get(tx.method, "OD")
            journal_lib = {
                "CA": "Caisse",
                "BQ": "Banque",
                "OD": "Opérations diverses",
            }.get(journal_code, "Divers")

            tiers_num, tiers_lib, treso_num, treso_lib = _get_accounts(tx)

            # Écriture 1 : compte de trésorerie
            if tx.direction == "IN":
                # Débit tréso / Crédit produit
                writer.writerow([
                    journal_code, journal_lib,
                    ecriture_num, ecriture_date,
                    treso_num, treso_lib,
                    "", "",
                    piece_ref, piece_date,
                    ecriture_lib,
                    montant, "0,00",
                    "", "", ecriture_date,
                    montant, "EUR",
                ])
                writer.writerow([
                    journal_code, journal_lib,
                    ecriture_num, ecriture_date,
                    tiers_num, tiers_lib,
                    "", "",
                    piece_ref, piece_date,
                    ecriture_lib,
                    "0,00", montant,
                    "", "", ecriture_date,
                    montant, "EUR",
                ])
            else:
                # Débit charge / Crédit tréso
                writer.writerow([
                    journal_code, journal_lib,
                    ecriture_num, ecriture_date,
                    tiers_num, tiers_lib,
                    "", "",
                    piece_ref, piece_date,
                    ecriture_lib,
                    montant, "0,00",
                    "", "", ecriture_date,
                    montant, "EUR",
                ])
                writer.writerow([
                    journal_code, journal_lib,
                    ecriture_num, ecriture_date,
                    treso_num, treso_lib,
                    "", "",
                    piece_ref, piece_date,
                    ecriture_lib,
                    "0,00", montant,
                    "", "", ecriture_date,
                    montant, "EUR",
                ])

        # BOM UTF-8 requis par la norme FEC
        content = "\ufeff" + output.getvalue()
        slug = mosque.slug or "mosquee"
        suffix = f"_{month_param:0>2}" if month_param else ""
        filename = f"FEC_{slug}_{year}{suffix}.txt"

        response = HttpResponse(
            content.encode("utf-8"),
            content_type="text/plain; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-FEC-Lines"] = str(len(transactions) * 2)
        response["X-FEC-Year"] = str(year)

        logger.info(
            "FEC EXPORT: mosque=%s year=%s transactions=%d lignes=%d",
            mosque.slug, year, len(transactions), len(transactions) * 2,
        )
        return response
