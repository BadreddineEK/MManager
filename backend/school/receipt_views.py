"""
Reçus PDF école coranique — school/receipt_views.py
====================================================
GET /api/school/payments/{id}/receipt/
    → Reçu PDF pour un paiement école (famille, enfant, année, montant)

Utilise reportlab pour générer le PDF à la volée.
"""
import io
from datetime import date

from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import HasMosquePermission
from .models import SchoolPayment

# ── Palette couleurs (même charte que treasury/receipt_views.py) ─────────────
COLOR_PRIMARY  = colors.HexColor("#1e3a5f")
COLOR_ACCENT   = colors.HexColor("#2563eb")
COLOR_GREEN    = colors.HexColor("#16a34a")
COLOR_LIGHT_BG = colors.HexColor("#f0f4ff")
COLOR_BORDER   = colors.HexColor("#dbeafe")
COLOR_MUTED    = colors.HexColor("#6b7280")
COLOR_TEXT     = colors.HexColor("#111827")
COLOR_WHITE    = colors.white


def _fmt_amount(amount):
    return f"{float(amount):,.2f} €".replace(",", "\u2009")  # espace fine


def _get_mosque_info(mosque):
    """Retourne les infos de la mosquée depuis MosqueSettings."""
    try:
        s = mosque.settings
        return {
            "name":          mosque.name,
            "address":       s.receipt_address or "",
            "phone":         s.receipt_phone or "",
            "legal_mention": s.receipt_legal_mention or "",
        }
    except Exception:
        return {"name": mosque.name, "address": "", "phone": "", "legal_mention": ""}


def _build_pdf_school_receipt(mosque_info, family_name, child_name, year_label,
                               payment_date, amount, method, note=""):
    """Génère le PDF d'un reçu de paiement école coranique."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    title_st  = ParagraphStyle("sc_title",  parent=normal, fontSize=20,
                                textColor=COLOR_PRIMARY, fontName="Helvetica-Bold", spaceAfter=2)
    sub_st    = ParagraphStyle("sc_sub",    parent=normal, fontSize=10,
                                textColor=COLOR_ACCENT,  fontName="Helvetica-Bold", spaceAfter=6)
    muted_st  = ParagraphStyle("sc_muted",  parent=normal, fontSize=8,
                                textColor=COLOR_MUTED,   leading=12)
    amount_st = ParagraphStyle("sc_amt",    parent=normal, fontSize=22,
                                textColor=COLOR_GREEN,   fontName="Helvetica-Bold", alignment=1)
    legal_st  = ParagraphStyle("sc_legal",  parent=normal, fontSize=7,
                                textColor=COLOR_MUTED,   leading=11, alignment=1)

    story = []

    # ── En-tête : nom mosquée + numéro de reçu ────────────────────────────────
    receipt_num = f"ECO-{payment_date.year}-{hash(f'{family_name}{payment_date}{amount}') % 1000000:06d}"

    header_data = [[
        Paragraph(
            f"<b>{mosque_info['name']}</b>",
            ParagraphStyle("mh", parent=normal, fontSize=13,
                           textColor=COLOR_PRIMARY, fontName="Helvetica-Bold"),
        ),
        Paragraph(
            f"<b>REÇU N° {receipt_num}</b>",
            ParagraphStyle("mrn", parent=normal, fontSize=11,
                           textColor=COLOR_WHITE, fontName="Helvetica-Bold", alignment=2),
        ),
    ]]
    header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (1, 0), (1, 0), COLOR_ACCENT),
        ("TEXTCOLOR",  (1, 0), (1, 0), COLOR_WHITE),
        ("ALIGN",      (1, 0), (1, 0), "RIGHT"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",    (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Adresse / téléphone mosquée
    addr_parts = []
    if mosque_info["address"]:
        addr_parts.append(mosque_info["address"].replace("\n", "<br/>"))
    if mosque_info["phone"]:
        addr_parts.append(f"📞 {mosque_info['phone']}")
    if addr_parts:
        story.append(Paragraph("<br/>".join(addr_parts), muted_st))
        story.append(Spacer(1, 2 * mm))

    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=5 * mm))

    # ── Titre du reçu ─────────────────────────────────────────────────────────
    story.append(Paragraph("🎓 REÇU DE PAIEMENT — ÉCOLE CORANIQUE", sub_st))
    story.append(Spacer(1, 2 * mm))

    # ── Montant mis en valeur ─────────────────────────────────────────────────
    story.append(Paragraph(_fmt_amount(amount), amount_st))
    story.append(Spacer(1, 3 * mm))

    # ── Tableau de détails ────────────────────────────────────────────────────
    method_labels = {
        "cash": "Espèces", "cheque": "Chèque",
        "virement": "Virement", "autre": "Autre",
    }

    details = [
        ["Famille :",         family_name],
        ["Élève :",           child_name or "—"],
        ["Année scolaire :",  year_label],
        ["Date :",            payment_date.strftime("%d/%m/%Y")],
        ["Mode de paiement :", method_labels.get(method, method)],
    ]
    if note:
        details.append(["Note :", note])
    details.append(["Émis le :", date.today().strftime("%d/%m/%Y")])

    detail_table = Table(details, colWidths=[45 * mm, 125 * mm])
    detail_table.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",      (0, 0), (0, -1), COLOR_MUTED),
        ("TEXTCOLOR",      (1, 0), (1, -1), COLOR_TEXT),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_LIGHT_BG, COLOR_WHITE]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 8 * mm))

    # ── Zone signature ────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER))
    story.append(Spacer(1, 4 * mm))

    sig_data = [[
        Paragraph(
            "<b>Pour la mosquée,</b><br/><br/><br/>_______________________<br/><i>Signature et cachet</i>",
            ParagraphStyle("sc_sig", parent=normal, fontSize=9, textColor=COLOR_TEXT, leading=14),
        ),
        Paragraph(
            f"<b>Émis le</b> {date.today().strftime('%d/%m/%Y')}<br/><br/>"
            f"<b>Reçu n°</b> {receipt_num}",
            ParagraphStyle("sc_info", parent=normal, fontSize=9, textColor=COLOR_MUTED, leading=14, alignment=2),
        ),
    ]]
    sig_table = Table(sig_data, colWidths=[85 * mm, 85 * mm])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sig_table)

    # ── Mention légale ────────────────────────────────────────────────────────
    if mosque_info["legal_mention"]:
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(mosque_info["legal_mention"], legal_st))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Vue API ───────────────────────────────────────────────────────────────────

class SchoolPaymentReceiptView(APIView):
    """
    GET /api/school/payments/{id}/receipt/
    Génère le PDF d'un reçu de paiement pour une famille de l'école coranique.
    """
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get(self, request, pk):
        # Dérive la mosquée depuis le paiement (évite le bug du fallback superuser)
        try:
            payment = SchoolPayment.objects.select_related(
                "mosque__settings", "family", "child", "school_year"
            ).get(pk=pk)
        except SchoolPayment.DoesNotExist:
            return Response({"detail": "Paiement introuvable."}, status=404)

        # Contrôle d'accès : utilisateur normal doit être sur la même mosquée
        request_mosque = getattr(request, "mosque", None)
        if request_mosque is not None and request_mosque != payment.mosque:
            return Response({"detail": "Paiement introuvable."}, status=404)

        mosque_info = _get_mosque_info(payment.mosque)
        family_name = payment.family.primary_contact_name
        child_name  = payment.child.first_name if payment.child else None
        year_label  = payment.school_year.label if payment.school_year else "—"

        pdf_bytes = _build_pdf_school_receipt(
            mosque_info  = mosque_info,
            family_name  = family_name,
            child_name   = child_name,
            year_label   = year_label,
            payment_date = payment.date,
            amount       = payment.amount,
            method       = payment.method,
            note         = payment.note,
        )

        safe_family = family_name.replace(" ", "_")
        filename    = f"recu_ecole_{safe_family}_{year_label}.pdf"
        response    = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
