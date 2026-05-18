"""
POST /api/school/payments/import/
==================================
Import en masse de paiements école par résolution nom famille/enfant.

Body JSON:
{
  "payments": [
    {
      "famille": "AARAB Zohir & Zeneb",
      "enfant": "Kawthar",        // optionnel
      "montant": 100,
      "date": "2025-09-01",
      "mode": "cheque",           // cash|cheque|virement|autre
      "note": "",
      "annee": "2025-2026"        // optionnel, auto-déduit depuis date
    }
  ]
}

Response:
{
  "success": 12,
  "errors": [{ "index": 3, "raison": "Famille 'XXX' introuvable" }]
}
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission
from core.utils import get_mosque, log_action
from .models import Child, Family, SchoolPayment, SchoolYear


METHOD_MAP = {
    "vir": "virement", "virement": "virement",
    "esp": "cash", "especes": "cash", "espèces": "cash", "cash": "cash",
    "chq": "cheque", "cheq": "cheque", "chèq": "cheque",
    "chèque": "cheque", "cheque": "cheque",
}


def _norm(s):
    return (s or "").strip().lower()


def _parse_date(val):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _parse_amount(val):
    try:
        return Decimal(str(val).replace(",", ".").strip())
    except (InvalidOperation, TypeError):
        return None


def _get_or_create_school_year(mosque, label):
    obj, _ = SchoolYear.objects.get_or_create(
        mosque=mosque, label=label,
        defaults={"is_active": False, "fee_amount": Decimal("0")},
    )
    return obj


class SchoolPaymentsImportView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def post(self, request):
        mosque = get_mosque(request)
        rows = request.data.get("payments", [])
        if not isinstance(rows, list):
            return Response({"error": "Le champ 'payments' doit être une liste."}, status=400)

        # Pré-charger familles et enfants de la mosquée en mémoire
        families = {_norm(f.primary_contact_name): f for f in Family.objects.filter(mosque=mosque)}
        children_by_family = {}
        for c in Child.objects.filter(mosque=mosque).select_related("family"):
            key = c.family_id
            children_by_family.setdefault(key, {})
            children_by_family[key][_norm(c.first_name)] = c

        school_year_cache = {}
        success = 0
        errors = []

        for i, row in enumerate(rows):
            # -- Résolution famille
            nom_famille = (row.get("famille") or "").strip()
            if not nom_famille:
                errors.append({"index": i, "raison": "Champ 'famille' manquant"})
                continue
            famille = families.get(_norm(nom_famille))
            if not famille:
                errors.append({"index": i, "raison": f"Famille '{nom_famille}' introuvable"})
                continue

            # -- Résolution enfant (optionnel)
            nom_enfant = (row.get("enfant") or "").strip()
            child = None
            if nom_enfant:
                child = children_by_family.get(famille.id, {}).get(_norm(nom_enfant))
                if not child:
                    errors.append({"index": i, "raison": f"Enfant '{nom_enfant}' introuvable dans la famille '{nom_famille}'"})
                    continue

            # -- Date
            date_val = _parse_date(row.get("date"))
            if not date_val:
                errors.append({"index": i, "raison": f"Date invalide : '{row.get('date')}'"})
                continue

            # -- Montant
            montant = _parse_amount(row.get("montant"))
            if montant is None or montant <= 0:
                errors.append({"index": i, "raison": f"Montant invalide : '{row.get('montant')}'"})
                continue

            # -- Mode paiement
            method = METHOD_MAP.get(_norm(row.get("mode") or ""), "autre")

            # -- Année scolaire
            annee_label = (row.get("annee") or "").strip()
            if not annee_label:
                y, m = date_val.year, date_val.month
                annee_label = f"{y}-{y+1}" if m >= 9 else f"{y-1}-{y}"
            if annee_label not in school_year_cache:
                school_year_cache[annee_label] = _get_or_create_school_year(mosque, annee_label)
            school_year = school_year_cache[annee_label]

            note = (row.get("note") or "").strip()

            try:
                with transaction.atomic():
                    # Idempotence : skip si paiement identique déjà présent
                    existing = SchoolPayment.objects.filter(
                        mosque=mosque, family=famille, child=child,
                        date=date_val, amount=montant,
                    ).first()
                    if existing:
                        continue  # déjà importé, on skip silencieusement

                    SchoolPayment.objects.create(
                        mosque=mosque,
                        family=famille,
                        child=child,
                        school_year=school_year,
                        date=date_val,
                        amount=montant,
                        method=method,
                        status="validated",
                        note=note,
                    )
                    success += 1
            except Exception as e:
                errors.append({"index": i, "raison": str(e)})

        log_action(request, "IMPORT", "SchoolPayment", None, {
            "success": success, "errors": len(errors)
        })

        return Response({"success": success, "errors": errors})
