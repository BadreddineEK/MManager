"""
Import bancaire CSV
POST /api/treasury/import/bank/
GET  /api/treasury/import/pending/
PATCH /api/treasury/import/pending/<id>/
"""
import csv
import io
import re
from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import BankAccount, DispatchRule, Staff
from core.permissions import HasMosquePermission, IsTresorierRole
from core.utils import get_mosque
from treasury.models import TreasuryTransaction
from treasury.serializers import TreasuryTransactionSerializer


def _parse_french_decimal(value):
    if not value or not value.strip():
        return None
    cleaned = value.strip().replace("\xa0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _detect_account_number(lines):
    for line in lines[:5]:
        match = re.search(r"[Nn]um[\xe9e]ro de compte\s*:\s*([\w]+)", line)
        if match:
            return match.group(1).strip()
    # Recherche plus large
    for line in lines[:5]:
        match = re.search(r"compte\s*:\s*([\d]+)", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _apply_dispatch_rules(rules, csv_label, csv_detail, direction):
    label_lower = csv_label.lower()
    detail_lower = csv_detail.lower()
    for rule in rules:
        if not rule.is_active:
            continue
        keyword = rule.keyword.lower()
        field = rule.field
        match = False
        if field == "label":
            match = keyword in label_lower
        elif field == "detail":
            match = keyword in detail_lower
        else:
            match = keyword in label_lower or keyword in detail_lower
        if not match:
            continue
        if rule.direction != "auto" and rule.direction != direction:
            continue
        return rule.category
    return None


def _parse_csv(file_content):
    text = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = file_content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = file_content.decode("latin-1", errors="replace")

    lines = text.splitlines()
    account_number = _detect_account_number(lines)

    header_idx = None
    for i, line in enumerate(lines):
        if re.search(r"[Dd]ate", line) and re.search(r"[Ll]ib", line):
            header_idx = i
            break

    if header_idx is None:
        return account_number, []

    data_text = "\n".join(lines[header_idx:])
    reader = csv.reader(io.StringIO(data_text), delimiter=";")
    headers = None
    transactions = []

    for row in reader:
        if headers is None:
            headers = [h.strip().lower() for h in row]
            continue
        if not row or not row[0].strip():
            continue
        if any("solde" in cell.lower() for cell in row if cell):
            continue
        try:
            row_date = row[0].strip() if len(row) > 0 else ""
            operation_id = row[1].strip() if len(row) > 1 else ""
            label = row[2].strip() if len(row) > 2 else ""
            debit_raw = row[3].strip() if len(row) > 3 else ""
            credit_raw = row[4].strip() if len(row) > 4 else ""
            detail = row[5].strip() if len(row) > 5 else ""
            if not re.match(r"\d{2}/\d{2}/\d{4}", row_date):
                continue
            debit = _parse_french_decimal(debit_raw)
            credit = _parse_french_decimal(credit_raw)
            transactions.append({
                "date": row_date,
                "operation_id": operation_id,
                "label": label,
                "detail": detail,
                "debit": debit,
                "credit": credit,
            })
        except (IndexError, ValueError):
            continue

    return account_number, transactions


class BankImportView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsTresorierRole]

    def post(self, request):
        mosque = get_mosque(request)
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response({"detail": "Aucun fichier fourni (champ file attendu)."}, status=400)

        file_content = csv_file.read()
        detected_account_number, rows = _parse_csv(file_content)

        if not rows:
            return Response({"detail": "Aucune transaction trouvee dans le fichier."}, status=400)

        bank_account_id = request.data.get("bank_account")
        bank_account = None

        if bank_account_id:
            try:
                bank_account = BankAccount.objects.get(pk=bank_account_id, mosque=mosque)
            except BankAccount.DoesNotExist:
                return Response({"detail": "Compte bancaire introuvable."}, status=404)
        elif detected_account_number:
            bank_account = BankAccount.objects.filter(
                mosque=mosque, account_number=detected_account_number
            ).first()
            if not bank_account:
                return Response(
                    {
                        "detail": f"Compte {detected_account_number} non configure. Ajoutez-le dans Parametres > Comptes bancaires.",
                        "detected_account_number": detected_account_number,
                    },
                    status=400,
                )
        else:
            return Response({"detail": "Impossible de detecter le numero de compte. Fournir bank_account (ID)."}, status=400)

        dispatch_rules = list(
            DispatchRule.objects.filter(mosque=mosque, is_active=True).order_by("priority", "keyword")
        )
        staff_keywords = list(
            Staff.objects.filter(mosque=mosque, is_active=True)
            .exclude(name_keyword="")
            .values_list("name_keyword", flat=True)
        )

        existing_ids = set(
            TreasuryTransaction.objects.filter(
                mosque=mosque, import_operation_id__isnull=False
            ).exclude(import_operation_id="").values_list("import_operation_id", flat=True)
        )

        imported_count = 0
        skipped_count = 0
        pending_count = 0
        created_transactions = []

        for row in rows:
            operation_id = row["operation_id"]
            if operation_id and operation_id in existing_ids:
                skipped_count += 1
                continue

            debit = row["debit"]
            credit = row["credit"]
            if credit is not None and credit > 0:
                direction = "IN"
                amount = credit
            elif debit is not None and debit != 0:
                direction = "OUT"
                amount = abs(debit)
            else:
                skipped_count += 1
                continue

            # Priorité 1 : matching staff (salaire)
            label_lower = row["label"].lower()
            detail_lower = row["detail"].lower()
            staff_match = any(
                kw.lower() in label_lower or kw.lower() in detail_lower
                for kw in staff_keywords
            )
            if staff_match and direction == "OUT":
                category = "salaire"
            else:
                category = _apply_dispatch_rules(dispatch_rules, row["label"], row["detail"], direction)
            import_stat = "validated" if category else "pending"
            if not category:
                pending_count += 1
                category = ""

            try:
                d, m, y = row["date"].split("/")
                date_iso = f"{y}-{m}-{d}"
            except ValueError:
                skipped_count += 1
                continue

            label = row["detail"].strip() if row["detail"].strip() else row["label"]

            tx = TreasuryTransaction(
                mosque=mosque,
                date=date_iso,
                category=category,
                label=label,
                direction=direction,
                amount=amount,
                method="virement",
                bank_account=bank_account,
                source="import",
                import_operation_id=operation_id if operation_id else None,
                import_status=import_stat,
                note=f"Import CSV — {row['label']}",
            )
            created_transactions.append(tx)
            if operation_id:
                existing_ids.add(operation_id)
            imported_count += 1

        TreasuryTransaction.objects.bulk_create(created_transactions)

        return Response(
            {
                "imported": imported_count,
                "skipped_duplicates": skipped_count,
                "pending_review": pending_count,
                "bank_account": bank_account.label,
                "detected_account_number": detected_account_number,
            },
            status=status.HTTP_201_CREATED,
        )


class ImportPendingListView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsTresorierRole]

    def get(self, request):
        mosque = get_mosque(request)
        qs = TreasuryTransaction.objects.filter(
            mosque=mosque, source="import", import_status="pending"
        ).order_by("-date", "-created_at")
        return Response(TreasuryTransactionSerializer(qs, many=True).data)


class ImportPendingDetailView(APIView):
    permission_classes = [IsAuthenticated, HasMosquePermission, IsTresorierRole]

    def patch(self, request, pk):
        mosque = get_mosque(request)
        try:
            tx = TreasuryTransaction.objects.get(pk=pk, mosque=mosque, source="import")
        except TreasuryTransaction.DoesNotExist:
            return Response({"detail": "Transaction introuvable."}, status=404)

        allowed_fields = {"category", "label", "note", "direction", "amount", "method", "regime_fiscal"}
        for field in allowed_fields:
            if field in request.data:
                setattr(tx, field, request.data[field])

        tx.import_status = "validated"
        tx.save()
        return Response(TreasuryTransactionSerializer(tx).data)
