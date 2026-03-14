"""
Backup & Restore — export ZIP multi-CSV + import ZIP.

Endpoints :
  GET  /api/backup/export/   → télécharge un ZIP contenant 8 CSV
  POST /api/backup/import/   → restaure depuis un ZIP uploadé

Seul le rôle ADMIN peut utiliser ces endpoints.
"""
import csv
import io
import zipfile
from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminRole
from core.models import Mosque
from membership.models import Member, MembershipPayment, MembershipYear
from school.models import Child, Family, SchoolPayment, SchoolYear
from treasury.models import TreasuryTransaction


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_csv(rows: list[dict], fieldnames: list[str]) -> str:
    """Retourne le contenu CSV (str) à partir d'une liste de dicts."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def _read_csv(content: bytes) -> list[dict]:
    """Parse un contenu CSV bytes → liste de dicts."""
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _str(val) -> str:
    return str(val) if val is not None else ""


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────────────────────

class BackupExportView(APIView):
    """
    GET /api/backup/export/
    Génère un ZIP contenant 8 fichiers CSV couvrant l'intégralité
    des données de la mosquée de l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        mosque: Mosque = request.user.mosque
        if not mosque:
            return Response({"detail": "Aucune mosquée associée."}, status=400)

        slug = mosque.slug
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"backup_{slug}_{ts}.zip"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

            # 1. school_years.csv
            rows = []
            for sy in SchoolYear.objects.filter(mosque=mosque):
                rows.append({
                    "id": sy.id, "label": sy.label,
                    "start_date": _str(sy.start_date), "end_date": _str(sy.end_date),
                    "is_active": sy.is_active,
                })
            zf.writestr("school_years.csv", _write_csv(rows,
                ["id", "label", "start_date", "end_date", "is_active"]))

            # 2. families.csv
            rows = []
            for f in Family.objects.filter(mosque=mosque):
                rows.append({
                    "id": f.id, "primary_contact_name": f.primary_contact_name,
                    "email": f.email, "phone1": f.phone1, "phone2": f.phone2,
                    "address": f.address, "created_at": _str(f.created_at),
                })
            zf.writestr("families.csv", _write_csv(rows,
                ["id", "primary_contact_name", "email", "phone1", "phone2", "address", "created_at"]))

            # 3. children.csv
            rows = []
            for c in Child.objects.filter(mosque=mosque).select_related("family"):
                rows.append({
                    "id": c.id, "family_id": c.family_id,
                    "family_name": c.family.primary_contact_name,
                    "first_name": c.first_name,
                    "birth_date": _str(c.birth_date), "level": c.level,
                    "created_at": _str(c.created_at),
                })
            zf.writestr("children.csv", _write_csv(rows,
                ["id", "family_id", "family_name", "first_name", "birth_date", "level", "created_at"]))

            # 4. school_payments.csv
            rows = []
            for p in SchoolPayment.objects.filter(mosque=mosque).select_related("family", "school_year", "child"):
                rows.append({
                    "id": p.id, "school_year": p.school_year.label,
                    "family_id": p.family_id,
                    "family_name": p.family.primary_contact_name,
                    "child_id": _str(p.child_id),
                    "child_name": p.child.first_name if p.child else "",
                    "date": _str(p.date), "amount": _str(p.amount),
                    "method": p.method, "note": p.note,
                    "created_at": _str(p.created_at),
                })
            zf.writestr("school_payments.csv", _write_csv(rows,
                ["id", "school_year", "family_id", "family_name", "child_id",
                 "child_name", "date", "amount", "method", "note", "created_at"]))

            # 5. membership_years.csv
            rows = []
            for my in MembershipYear.objects.filter(mosque=mosque):
                rows.append({
                    "id": my.id, "year": my.year,
                    "amount_expected": _str(my.amount_expected),
                    "is_active": my.is_active,
                })
            zf.writestr("membership_years.csv", _write_csv(rows,
                ["id", "year", "amount_expected", "is_active"]))

            # 6. members.csv
            rows = []
            for m in Member.objects.filter(mosque=mosque):
                rows.append({
                    "id": m.id, "full_name": m.full_name, "email": m.email,
                    "phone": m.phone, "address": m.address,
                    "created_at": _str(m.created_at),
                })
            zf.writestr("members.csv", _write_csv(rows,
                ["id", "full_name", "email", "phone", "address", "created_at"]))

            # 7. membership_payments.csv
            rows = []
            for mp in MembershipPayment.objects.filter(mosque=mosque).select_related("member", "membership_year"):
                rows.append({
                    "id": mp.id, "membership_year": mp.membership_year.year,
                    "member_id": mp.member_id,
                    "member_name": mp.member.full_name,
                    "date": _str(mp.date), "amount": _str(mp.amount),
                    "method": mp.method, "note": mp.note,
                    "created_at": _str(mp.created_at),
                })
            zf.writestr("membership_payments.csv", _write_csv(rows,
                ["id", "membership_year", "member_id", "member_name",
                 "date", "amount", "method", "note", "created_at"]))

            # 8. treasury_transactions.csv
            rows = []
            for t in TreasuryTransaction.objects.filter(mosque=mosque):
                rows.append({
                    "id": t.id, "date": _str(t.date), "category": t.category,
                    "label": t.label, "direction": t.direction,
                    "amount": _str(t.amount), "method": t.method,
                    "note": t.note, "created_at": _str(t.created_at),
                })
            zf.writestr("treasury_transactions.csv", _write_csv(rows,
                ["id", "date", "category", "label", "direction",
                 "amount", "method", "note", "created_at"]))

            # 9. README.txt — mode d'emploi
            readme = (
                f"Backup Mosquée Manager\n"
                f"Mosquée  : {mosque.name} ({slug})\n"
                f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}\n\n"
                "Fichiers inclus :\n"
                "  school_years.csv         — Années scolaires\n"
                "  families.csv             — Familles école coranique\n"
                "  children.csv             — Enfants\n"
                "  school_payments.csv      — Paiements école\n"
                "  membership_years.csv     — Années de cotisation\n"
                "  members.csv              — Adhérents\n"
                "  membership_payments.csv  — Paiements cotisations\n"
                "  treasury_transactions.csv — Transactions trésorerie\n\n"
                "Import : Settings > Sauvegarde > Restaurer depuis un ZIP\n"
                "ATTENTION : l'import FUSIONNE les données (pas d'écrasement).\n"
                "Les enregistrements existants (même ID) sont ignorés.\n"
            )
            zf.writestr("README.txt", readme)

        buf.seek(0)
        resp = HttpResponse(buf.read(), content_type="application/zip")
        resp["Content-Disposition"] = f'attachment; filename="{zip_name}"'
        return resp


# ─────────────────────────────────────────────────────────────────────────────
# IMPORT
# ─────────────────────────────────────────────────────────────────────────────

class BackupImportView(APIView):
    """
    POST /api/backup/import/   (multipart/form-data, champ : file)
    Restaure les données depuis un ZIP généré par BackupExportView.
    Mode FUSION : les enregistrements déjà présents sont ignorés.
    Retourne un rapport JSON avec le nombre d'objets créés par table.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]
    parser_classes = [MultiPartParser]

    def post(self, request):
        mosque: Mosque = request.user.mosque
        if not mosque:
            return Response({"detail": "Aucune mosquée associée."}, status=400)

        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"detail": "Champ 'file' manquant."}, status=400)

        if not uploaded.name.endswith(".zip"):
            return Response({"detail": "Le fichier doit être un .zip"}, status=400)

        report = {}
        errors = []

        try:
            with zipfile.ZipFile(io.BytesIO(uploaded.read())) as zf:
                names = zf.namelist()

                # ── school_years ──────────────────────────────────────────
                if "school_years.csv" in names:
                    rows = _read_csv(zf.read("school_years.csv"))
                    created = 0
                    for r in rows:
                        try:
                            _, is_new = SchoolYear.objects.get_or_create(
                                mosque=mosque, label=r["label"],
                                defaults={
                                    "start_date": r["start_date"] or "2000-01-01",
                                    "end_date":   r["end_date"]   or "2000-12-31",
                                    "is_active":  r.get("is_active", "False") == "True",
                                },
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"school_years: {e}")
                    report["school_years"] = created

                # ── families ─────────────────────────────────────────────
                if "families.csv" in names:
                    rows = _read_csv(zf.read("families.csv"))
                    created = 0
                    for r in rows:
                        try:
                            _, is_new = Family.objects.get_or_create(
                                mosque=mosque,
                                primary_contact_name=r["primary_contact_name"],
                                phone1=r["phone1"],
                                defaults={
                                    "email":   r.get("email", ""),
                                    "phone2":  r.get("phone2", ""),
                                    "address": r.get("address", ""),
                                },
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"families: {e}")
                    report["families"] = created

                # ── children ─────────────────────────────────────────────
                if "children.csv" in names:
                    rows = _read_csv(zf.read("children.csv"))
                    created = 0
                    for r in rows:
                        try:
                            family = Family.objects.filter(
                                mosque=mosque,
                                primary_contact_name=r.get("family_name", "")
                            ).first()
                            if not family:
                                errors.append(f"children: famille introuvable '{r.get('family_name')}'")
                                continue
                            _, is_new = Child.objects.get_or_create(
                                mosque=mosque, family=family,
                                first_name=r["first_name"],
                                defaults={
                                    "birth_date": r["birth_date"] or None,
                                    "level":      r.get("level", ""),
                                },
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"children: {e}")
                    report["children"] = created

                # ── school_payments ───────────────────────────────────────
                if "school_payments.csv" in names:
                    rows = _read_csv(zf.read("school_payments.csv"))
                    created = 0
                    for r in rows:
                        try:
                            sy = SchoolYear.objects.filter(mosque=mosque, label=r["school_year"]).first()
                            fam = Family.objects.filter(mosque=mosque, primary_contact_name=r.get("family_name","")).first()
                            if not sy or not fam:
                                continue
                            _, is_new = SchoolPayment.objects.get_or_create(
                                mosque=mosque, school_year=sy, family=fam,
                                date=r["date"], amount=r["amount"],
                                defaults={"method": r.get("method","cash"), "note": r.get("note","")},
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"school_payments: {e}")
                    report["school_payments"] = created

                # ── membership_years ──────────────────────────────────────
                if "membership_years.csv" in names:
                    rows = _read_csv(zf.read("membership_years.csv"))
                    created = 0
                    for r in rows:
                        try:
                            _, is_new = MembershipYear.objects.get_or_create(
                                mosque=mosque, year=int(r["year"]),
                                defaults={
                                    "amount_expected": r.get("amount_expected", 0),
                                    "is_active": r.get("is_active", "False") == "True",
                                },
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"membership_years: {e}")
                    report["membership_years"] = created

                # ── members ───────────────────────────────────────────────
                if "members.csv" in names:
                    rows = _read_csv(zf.read("members.csv"))
                    created = 0
                    for r in rows:
                        try:
                            _, is_new = Member.objects.get_or_create(
                                mosque=mosque,
                                full_name=r["full_name"],
                                phone=r.get("phone",""),
                                defaults={
                                    "email":   r.get("email",""),
                                    "address": r.get("address",""),
                                },
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"members: {e}")
                    report["members"] = created

                # ── membership_payments ───────────────────────────────────
                if "membership_payments.csv" in names:
                    rows = _read_csv(zf.read("membership_payments.csv"))
                    created = 0
                    for r in rows:
                        try:
                            my = MembershipYear.objects.filter(mosque=mosque, year=r["membership_year"]).first()
                            mem = Member.objects.filter(mosque=mosque, full_name=r.get("member_name","")).first()
                            if not my or not mem:
                                continue
                            _, is_new = MembershipPayment.objects.get_or_create(
                                mosque=mosque, membership_year=my, member=mem,
                                date=r["date"], amount=r["amount"],
                                defaults={"method": r.get("method","cash"), "note": r.get("note","")},
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"membership_payments: {e}")
                    report["membership_payments"] = created

                # ── treasury_transactions ─────────────────────────────────
                if "treasury_transactions.csv" in names:
                    rows = _read_csv(zf.read("treasury_transactions.csv"))
                    created = 0
                    for r in rows:
                        try:
                            _, is_new = TreasuryTransaction.objects.get_or_create(
                                mosque=mosque,
                                date=r["date"], label=r["label"],
                                direction=r["direction"], amount=r["amount"],
                                defaults={
                                    "category": r.get("category","autre"),
                                    "method":   r.get("method","cash"),
                                    "note":     r.get("note",""),
                                },
                            )
                            if is_new:
                                created += 1
                        except Exception as e:
                            errors.append(f"treasury: {e}")
                    report["treasury_transactions"] = created

        except zipfile.BadZipFile:
            return Response({"detail": "Fichier ZIP invalide ou corrompu."}, status=400)
        except Exception as e:
            return Response({"detail": f"Erreur inattendue : {e}"}, status=500)

        return Response({
            "status": "ok",
            "mosque": mosque.name,
            "created": report,
            "errors": errors[:20],  # max 20 erreurs dans la réponse
            "total_created": sum(report.values()),
        }, status=status.HTTP_200_OK)
