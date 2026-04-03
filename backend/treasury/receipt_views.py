"""
Vues Reçus fiscaux PDF — treasury/receipt_views.py
====================================================
GET /api/treasury/receipt/transaction/{id}/
    → Reçu PDF pour une transaction (don IN)

GET /api/treasury/receipt/donor/?name=Ahmed&year=2025
    → Récapitulatif annuel de tous les dons d'un donateur (libre, par nom)

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
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.permissions import HasMosquePermission
from core.utils import get_mosque
from .models import TreasuryTransaction


# ── Palette couleurs ─────────────────────────────────────────────────────────
COLOR_PRIMARY   = colors.HexColor("#1e3a5f")   # bleu foncé
COLOR_ACCENT    = colors.HexColor("#2563eb")   # bleu vif
COLOR_GREEN     = colors.HexColor("#16a34a")
COLOR_LIGHT_BG  = colors.HexColor("#f0f4ff")
COLOR_BORDER    = colors.HexColor("#dbeafe")
COLOR_MUTED     = colors.HexColor("#6b7280")
COLOR_TEXT      = colors.HexColor("#111827")
COLOR_1901      = colors.HexColor("#1d4ed8")
COLOR_1905      = colors.HexColor("#7c3aed")
COLOR_WHITE     = colors.white


def _get_settings(mosque):
    """Retourne les infos du reçu depuis MosqueSettings."""
    try:
        s = mosque.settings
        return {
            "name":          mosque.name,
            "address":       s.receipt_address or "",
            "phone":         s.receipt_phone or "",
            "logo_url":      s.receipt_logo_url or "",
            "legal_mention": s.receipt_legal_mention or "",
        }
    except Exception:
        return {
            "name":          mosque.name,
            "address":       "",
            "phone":         "",
            "logo_url":      "",
            "legal_mention": "",
        }


def _fmt_amount(amount):
    return f"{float(amount):,.2f} €".replace(",", "\u2009")  # espace fine


def _regime_label(regime):
    if regime == "1901":
        return "Loi 1901 — Association"
    if regime == "1905":
        return "Loi 1905 — Culte"
    return ""


def _build_pdf_receipt(mosque_info, receipt_num, tx_date, label, amount, regime, donor_name="", note=""):
    """
    Génère le PDF d'un reçu unique et retourne les bytes.
    """
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
    normal   = styles["Normal"]
    title_st = ParagraphStyle("title_st",   parent=normal, fontSize=20, textColor=COLOR_PRIMARY,  fontName="Helvetica-Bold", spaceAfter=2)
    sub_st   = ParagraphStyle("sub_st",     parent=normal, fontSize=10, textColor=COLOR_ACCENT,   fontName="Helvetica-Bold", spaceAfter=6)
    body_st  = ParagraphStyle("body_st",    parent=normal, fontSize=9,  textColor=COLOR_TEXT,     leading=14)
    muted_st = ParagraphStyle("muted_st",   parent=normal, fontSize=8,  textColor=COLOR_MUTED,    leading=12)
    amount_st= ParagraphStyle("amount_st",  parent=normal, fontSize=22, textColor=COLOR_GREEN,    fontName="Helvetica-Bold", alignment=1)
    legal_st = ParagraphStyle("legal_st",   parent=normal, fontSize=7,  textColor=COLOR_MUTED,    leading=11, alignment=1)

    story = []

    # ── En-tête mosquée ───────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"<b>{mosque_info['name']}</b>", ParagraphStyle("h", parent=normal, fontSize=13, textColor=COLOR_PRIMARY, fontName="Helvetica-Bold")),
        Paragraph(f"<b>REÇU N° {receipt_num}</b>", ParagraphStyle("rn", parent=normal, fontSize=11, textColor=COLOR_WHITE, fontName="Helvetica-Bold", alignment=2)),
    ]]
    header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (1, 0), (1, 0), COLOR_ACCENT),
        ("TEXTCOLOR",    (1, 0), (1, 0), COLOR_WHITE),
        ("ALIGN",        (1, 0), (1, 0), "RIGHT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",      (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    # Adresse + téléphone
    addr_parts = []
    if mosque_info["address"]:
        addr_parts.append(mosque_info["address"].replace("\n", "<br/>"))
    if mosque_info["phone"]:
        addr_parts.append(f"📞 {mosque_info['phone']}")
    if addr_parts:
        story.append(Paragraph("<br/>".join(addr_parts), muted_st))
        story.append(Spacer(1, 2 * mm))

    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=5 * mm))

    # ── Titre reçu ────────────────────────────────────────────────────────────
    story.append(Paragraph("🧾 REÇU DE DON / PAIEMENT", sub_st))
    story.append(Spacer(1, 2 * mm))

    # Bloc montant
    story.append(Paragraph(_fmt_amount(amount), amount_st))
    story.append(Spacer(1, 3 * mm))

    # ── Détails transaction ───────────────────────────────────────────────────
    details = [
        ["Date :", str(tx_date)],
        ["Libellé :", label],
    ]
    if donor_name:
        details.append(["Donateur :", donor_name])
    if regime:
        details.append(["Régime fiscal :", _regime_label(regime)])
    if note:
        details.append(["Note :", note])
    details.append(["Reçu le :", date.today().strftime("%d/%m/%Y")])

    detail_table = Table(details, colWidths=[35 * mm, 135 * mm])
    detail_table.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",    (0, 0), (0, -1), COLOR_MUTED),
        ("TEXTCOLOR",    (1, 0), (1, -1), COLOR_TEXT),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLOR_LIGHT_BG, COLOR_WHITE]),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 6 * mm))

    # ── Badge régime ──────────────────────────────────────────────────────────
    if regime in ("1901", "1905"):
        badge_color = COLOR_1901 if regime == "1901" else COLOR_1905
        badge_label = f"  ⚖️  {_regime_label(regime)}  "
        badge_table = Table([[Paragraph(badge_label, ParagraphStyle("badge", parent=normal, fontSize=8, textColor=COLOR_WHITE, fontName="Helvetica-Bold"))]],
                            colWidths=[80 * mm])
        badge_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0), badge_color),
            ("ALIGN",         (0, 0), (0, 0), "LEFT"),
            ("PADDING",       (0, 0), (-1, -1), 6),
            ("ROUNDEDCORNERS", [4]),
        ]))
        story.append(badge_table)
        story.append(Spacer(1, 5 * mm))

    # ── Signature ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER))
    story.append(Spacer(1, 4 * mm))
    sig_data = [[
        Paragraph("<b>Pour la mosquée,</b><br/><br/><br/>_______________________<br/><i>Signature et cachet</i>",
                  ParagraphStyle("sig", parent=normal, fontSize=9, textColor=COLOR_TEXT, leading=14)),
        Paragraph(f"<b>Émis le</b> {date.today().strftime('%d/%m/%Y')}<br/><br/>"
                  f"<b>Reçu n°</b> {receipt_num}",
                  ParagraphStyle("info", parent=normal, fontSize=9, textColor=COLOR_MUTED, leading=14, alignment=2)),
    ]]
    sig_table = Table(sig_data, colWidths=[85 * mm, 85 * mm])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
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


def _build_pdf_annual_summary(mosque_info, year, transactions):
    """
    Génère le bilan financier annuel PDF.
    Contenu :
      - Tableau détaillé de toutes les transactions (IN et OUT) triées par date
      - Synthèse par catégorie (total IN et OUT par catégorie)
      - Récapitulatif final : total entrées / sorties / solde net
    """
    from collections import defaultdict

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
    normal   = styles["Normal"]
    title_st = ParagraphStyle("t",   parent=normal, fontSize=16, textColor=COLOR_PRIMARY, fontName="Helvetica-Bold", spaceAfter=4)
    sub_st   = ParagraphStyle("s",   parent=normal, fontSize=10, textColor=COLOR_ACCENT,  fontName="Helvetica-Bold", spaceAfter=4, spaceBefore=8)
    muted_st = ParagraphStyle("m",   parent=normal, fontSize=8,  textColor=COLOR_MUTED,   leading=12)
    legal_st = ParagraphStyle("l",   parent=normal, fontSize=7,  textColor=COLOR_MUTED,   leading=11, alignment=1)
    bal_st   = ParagraphStyle("bal", parent=normal, fontSize=13, textColor=COLOR_GREEN,   fontName="Helvetica-Bold", alignment=1, spaceBefore=6)

    story = []

    # ── En-tête mosquée ───────────────────────────────────────────────────────
    story.append(Paragraph(mosque_info["name"], title_st))
    addr_parts = []
    if mosque_info["address"]:
        addr_parts.append(mosque_info["address"].replace("\n", "<br/>"))
    if mosque_info["phone"]:
        addr_parts.append(f"📞 {mosque_info['phone']}")
    if addr_parts:
        story.append(Paragraph("<br/>".join(addr_parts), muted_st))
    story.append(Spacer(1, 3 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=4 * mm))

    story.append(Paragraph(f"📊 BILAN FINANCIER {year}", sub_st))
    story.append(Paragraph(f"<b>Émis le :</b> {date.today().strftime('%d/%m/%Y')}", muted_st))
    story.append(Spacer(1, 5 * mm))

    # ── Totaux globaux ────────────────────────────────────────────────────────
    total_in  = sum(float(tx.amount) for tx in transactions if tx.direction == "IN")
    total_out = sum(float(tx.amount) for tx in transactions if tx.direction == "OUT")
    balance   = total_in - total_out

    bal_color = COLOR_GREEN if balance >= 0 else colors.HexColor("#dc2626")
    bal_sign  = "+" if balance >= 0 else ""

    kpi_data = [[
        Paragraph(f"<b>Entrées</b><br/>{_fmt_amount(total_in)}",
                  ParagraphStyle("ki", parent=normal, fontSize=10, textColor=COLOR_GREEN, fontName="Helvetica-Bold", alignment=1)),
        Paragraph(f"<b>Sorties</b><br/>{_fmt_amount(total_out)}",
                  ParagraphStyle("ko", parent=normal, fontSize=10, textColor=colors.HexColor("#dc2626"), fontName="Helvetica-Bold", alignment=1)),
        Paragraph(f"<b>Solde net</b><br/>{bal_sign}{_fmt_amount(balance)}",
                  ParagraphStyle("kb", parent=normal, fontSize=10, textColor=bal_color, fontName="Helvetica-Bold", alignment=1)),
    ]]
    kpi_table = Table(kpi_data, colWidths=[55 * mm, 55 * mm, 55 * mm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), colors.HexColor("#dcfce7")),
        ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#fee2e2")),
        ("BACKGROUND",    (2, 0), (2, 0), COLOR_LIGHT_BG),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 6 * mm))

    # ── Synthèse par catégorie ────────────────────────────────────────────────
    story.append(Paragraph("Synthèse par catégorie", sub_st))

    cat_totals = defaultdict(lambda: {"IN": 0.0, "OUT": 0.0})
    for tx in transactions:
        cat_totals[tx.category][tx.direction] += float(tx.amount)

    cat_data = [["Catégorie", "Entrées", "Sorties", "Solde"]]
    for cat in sorted(cat_totals.keys()):
        cin  = cat_totals[cat]["IN"]
        cout = cat_totals[cat]["OUT"]
        sol  = cin - cout
        sign = "+" if sol >= 0 else ""
        cat_data.append([cat.capitalize(), _fmt_amount(cin), _fmt_amount(cout), f"{sign}{_fmt_amount(sol)}"])

    cat_table = Table(cat_data, colWidths=[55 * mm, 40 * mm, 40 * mm, 40 * mm], repeatRows=1)
    cat_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), COLOR_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ("LINEBELOW",     (0, 0), (-1, 0),  1,   COLOR_PRIMARY),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 6 * mm))

    # ── Tableau détaillé de toutes les transactions ───────────────────────────
    story.append(Paragraph("Journal des transactions", sub_st))

    tx_data = [["Date", "Sens", "Catégorie", "Libellé", "Montant"]]
    for tx in sorted(transactions, key=lambda x: x.date):
        sens = "▲ Entrée" if tx.direction == "IN" else "▼ Sortie"
        tx_data.append([
            tx.date.strftime("%d/%m/%Y"),
            sens,
            tx.category.capitalize(),
            tx.label[:50] + ("…" if len(tx.label) > 50 else ""),
            _fmt_amount(tx.amount),
        ])

    tx_table = Table(tx_data, colWidths=[22 * mm, 20 * mm, 25 * mm, 85 * mm, 23 * mm], repeatRows=1)
    ts = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), COLOR_PRIMARY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), COLOR_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
        ("ALIGN",         (4, 0), (4, -1), "RIGHT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [COLOR_WHITE, COLOR_LIGHT_BG]),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("GRID",          (0, 0), (-1, -1), 0.3, COLOR_BORDER),
        ("LINEBELOW",     (0, 0), (-1, 0),  1,   COLOR_PRIMARY),
    ])
    # Colorer la colonne "Sens" en vert/rouge selon direction
    for i, tx in enumerate(sorted(transactions, key=lambda x: x.date), start=1):
        color = colors.HexColor("#16a34a") if tx.direction == "IN" else colors.HexColor("#dc2626")
        ts.add("TEXTCOLOR", (1, i), (1, i), color)
        ts.add("FONTNAME",  (1, i), (1, i), "Helvetica-Bold")
    tx_table.setStyle(ts)
    story.append(tx_table)

    # ── Mention légale ────────────────────────────────────────────────────────
    if mosque_info["legal_mention"]:
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(mosque_info["legal_mention"], legal_st))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# ── Vues API ─────────────────────────────────────────────────────────────────

class TransactionReceiptView(APIView):
    """
    GET /api/treasury/receipt/transaction/{id}/
    Génère le PDF d'un reçu pour une transaction donnée.
    ?donor=Nom Prénom   → nom du donateur à afficher (optionnel)
    """
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get(self, request, pk):
        # Récupère la transaction en premier pour dériver la mosquée depuis l'objet
        # (évite le bug du fallback superuser qui renverrait toujours mosque 1)
        try:
            tx = TreasuryTransaction.objects.select_related("mosque__settings").get(pk=pk)
        except TreasuryTransaction.DoesNotExist:
            return Response({"detail": "Transaction introuvable."}, status=404)

        # Vérification d'accès : superuser peut tout voir, sinon doit être sur la même mosquée
        request_mosque = getattr(request, "mosque", None)
        if request_mosque is not None and request_mosque != tx.mosque:
            return Response({"detail": "Transaction introuvable."}, status=404)

        mosque = tx.mosque

        mosque_info = _get_settings(mosque)
        donor_name  = request.query_params.get("donor", "")
        receipt_num = f"{tx.date.year}-{tx.id:06d}"

        pdf_bytes = _build_pdf_receipt(
            mosque_info  = mosque_info,
            receipt_num  = receipt_num,
            tx_date      = tx.date,
            label        = tx.label,
            amount       = tx.amount,
            regime       = tx.regime_fiscal,
            donor_name   = donor_name,
            note         = tx.note,
        )

        filename = f"recu_{receipt_num}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AnnualSummaryReceiptView(APIView):
    """
    GET /api/treasury/receipt/annual/?year=2025
    Bilan financier annuel complet :
      - KPIs : total entrées / sorties / solde
      - Synthèse par catégorie
      - Journal détaillé de toutes les transactions de l'année
    Filtre optionnel : ?category=don  (restreint à une catégorie)
    """
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get(self, request):
        mosque = getattr(request, "mosque", None)
        if mosque is None:
            return Response({"detail": "Mosquée non déterminée."}, status=400)

        year_param = request.query_params.get("year", str(date.today().year))
        category   = request.query_params.get("category", "").strip()

        try:
            year = int(year_param)
        except ValueError:
            return Response({"detail": "Paramètre year invalide."}, status=400)

        qs = TreasuryTransaction.objects.filter(
            mosque=mosque,
            date__year=year,
        ).order_by("date")

        if category:
            qs = qs.filter(category=category)

        transactions = list(qs)

        if not transactions:
            return Response({"detail": f"Aucune transaction en {year}."}, status=404)

        mosque_info = _get_settings(mosque)
        pdf_bytes = _build_pdf_annual_summary(
            mosque_info  = mosque_info,
            year         = year,
            transactions = transactions,
        )

        suffix   = f"_{category}" if category else ""
        filename = f"bilan_{year}{suffix}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ── Reçu de cotisation (adhérent) ────────────────────────────────────────────

def _build_pdf_membership_receipt(mosque_info, member_name, payment_date, amount, year_label, method, note=""):
    """
    Génère le PDF d'un reçu de cotisation pour un adhérent.
    """
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
    normal   = styles["Normal"]
    title_st = ParagraphStyle("m_title",  parent=normal, fontSize=20, textColor=COLOR_PRIMARY, fontName="Helvetica-Bold", spaceAfter=2)
    sub_st   = ParagraphStyle("m_sub",    parent=normal, fontSize=10, textColor=COLOR_ACCENT,  fontName="Helvetica-Bold", spaceAfter=6)
    muted_st = ParagraphStyle("m_muted",  parent=normal, fontSize=8,  textColor=COLOR_MUTED,   leading=12)
    amount_st= ParagraphStyle("m_amt",    parent=normal, fontSize=22, textColor=COLOR_GREEN,   fontName="Helvetica-Bold", alignment=1)
    legal_st = ParagraphStyle("m_legal",  parent=normal, fontSize=7,  textColor=COLOR_MUTED,   leading=11, alignment=1)

    story = []

    # En-tête mosquée + numéro de reçu
    receipt_num = f"ADH-{payment_date.year}-{hash(f'{member_name}{payment_date}') % 1000000:06d}"
    header_data = [[
        Paragraph(f"<b>{mosque_info['name']}</b>",
                  ParagraphStyle("mh", parent=normal, fontSize=13, textColor=COLOR_PRIMARY, fontName="Helvetica-Bold")),
        Paragraph(f"<b>REÇU N° {receipt_num}</b>",
                  ParagraphStyle("mrn", parent=normal, fontSize=11, textColor=COLOR_WHITE, fontName="Helvetica-Bold", alignment=2)),
    ]]
    header_table = Table(header_data, colWidths=[110 * mm, 60 * mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (1, 0), (1, 0), COLOR_ACCENT),
        ("TEXTCOLOR",    (1, 0), (1, 0), COLOR_WHITE),
        ("ALIGN",        (1, 0), (1, 0), "RIGHT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING",      (0, 0), (-1, -1), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))

    addr_parts = []
    if mosque_info["address"]:
        addr_parts.append(mosque_info["address"].replace("\n", "<br/>"))
    if mosque_info["phone"]:
        addr_parts.append(f"📞 {mosque_info['phone']}")
    if addr_parts:
        story.append(Paragraph("<br/>".join(addr_parts), muted_st))
        story.append(Spacer(1, 2 * mm))

    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=5 * mm))

    # Titre
    story.append(Paragraph("🪙 REÇU DE COTISATION", sub_st))
    story.append(Spacer(1, 2 * mm))

    # Montant
    story.append(Paragraph(_fmt_amount(amount), amount_st))
    story.append(Spacer(1, 3 * mm))

    # Détails
    method_labels = {
        "cash": "Espèces", "cheque": "Chèque",
        "virement": "Virement", "autre": "Autre",
    }
    details = [
        ["Adhérent :",      member_name],
        ["Année :",         year_label],
        ["Date :",          payment_date.strftime("%d/%m/%Y")],
        ["Mode :",          method_labels.get(method, method)],
    ]
    if note:
        details.append(["Note :", note])
    details.append(["Émis le :", date.today().strftime("%d/%m/%Y")])

    detail_table = Table(details, colWidths=[35 * mm, 135 * mm])
    detail_table.setStyle(TableStyle([
        ("FONTNAME",        (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",        (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",       (0, 0), (0, -1), COLOR_MUTED),
        ("TEXTCOLOR",       (1, 0), (1, -1), COLOR_TEXT),
        ("TOPPADDING",      (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",   (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS",  (0, 0), (-1, -1), [COLOR_LIGHT_BG, COLOR_WHITE]),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 8 * mm))

    # Signature
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER))
    story.append(Spacer(1, 4 * mm))
    sig_data = [[
        Paragraph("<b>Pour la mosquée,</b><br/><br/><br/>_______________________<br/><i>Signature et cachet</i>",
                  ParagraphStyle("ms", parent=normal, fontSize=9, textColor=COLOR_TEXT, leading=14)),
        Paragraph(f"<b>Émis le</b> {date.today().strftime('%d/%m/%Y')}<br/><br/>"
                  f"<b>Reçu n°</b> {receipt_num}",
                  ParagraphStyle("mi", parent=normal, fontSize=9, textColor=COLOR_MUTED, leading=14, alignment=2)),
    ]]
    sig_table = Table(sig_data, colWidths=[85 * mm, 85 * mm])
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sig_table)

    if mosque_info["legal_mention"]:
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(mosque_info["legal_mention"], legal_st))

    doc.build(story)
    buf.seek(0)
    return buf.read()


class MembershipPaymentReceiptView(APIView):
    """
    GET /api/treasury/receipt/membership/{id}/
    Génère le PDF d'un reçu de cotisation depuis une TreasuryTransaction
    (category='cotisation', direction='IN').
    """
    permission_classes = [IsAuthenticated, HasMosquePermission]

    def get(self, request, pk):
        try:
            tx = TreasuryTransaction.objects.select_related(
                "member", "membership_year", "mosque__settings"
            ).get(pk=pk, category="cotisation")
        except TreasuryTransaction.DoesNotExist:
            return Response({"detail": "Transaction de cotisation introuvable."}, status=404)

        # Contrôle d'accès
        request_mosque = getattr(request, "mosque", None)
        if request_mosque is not None and request_mosque != tx.mosque:
            return Response({"detail": "Transaction introuvable."}, status=404)

        mosque_info = _get_settings(tx.mosque)
        member_name = tx.member.full_name if tx.member else (tx.label or "—")
        year_label  = str(tx.membership_year.year) if tx.membership_year else "—"

        pdf_bytes = _build_pdf_membership_receipt(
            mosque_info  = mosque_info,
            member_name  = member_name,
            payment_date = tx.date,
            amount       = tx.amount,
            year_label   = year_label,
            method       = tx.method,
            note         = tx.note,
        )

        safe_name = member_name.replace(" ", "_")
        filename  = f"cotisation_{safe_name}_{year_label}.pdf"
        response  = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
