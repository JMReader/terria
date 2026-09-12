"""PDF del certificado TERRIA (datos + portada NDVI).

No necesita navegador: compone el documento con ReportLab a partir del mismo
`CertificationDocumentResponse` que alimenta la ficha HTML.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.blockchain.schemas import CertificationDocumentResponse

BRAND = colors.HexColor("#0A7D33")
BRAND_DARK = colors.HexColor("#075C25")
INK = colors.HexColor("#14261C")
MUTED = colors.HexColor("#5B6B61")
LINE = colors.HexColor("#D9E2DB")
PANEL = colors.HexColor("#F6FAF7")
STATUS_COLOR = {
    "verified": colors.HexColor("#0A7D33"),
    "tampered": colors.HexColor("#B00020"),
    "pending": colors.HexColor("#8A6D00"),
    "rpc_unavailable": colors.HexColor("#8A6D00"),
}
STATUS_LABEL = {
    "verified": "VERIFICADO",
    "tampered": "ALTERADO",
    "pending": "PENDIENTE",
    "rpc_unavailable": "RPC NO DISPONIBLE",
}


def _num(value, factor: float, digits: int) -> str:
    if value is None:
        return "—"
    return f"{value / factor:.{digits}f}"


def _date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%d/%m/%Y")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=26, leading=28, textColor=BRAND_DARK, alignment=TA_LEFT,
                                spaceAfter=0),
        "tag": ParagraphStyle("tag", parent=base["Normal"], fontName="Helvetica",
                              fontSize=8, textColor=MUTED, leading=11),
        "doctitle": ParagraphStyle("doctitle", parent=base["Normal"], fontName="Helvetica-Bold",
                                   fontSize=15, textColor=INK, alignment=2, leading=18),
        "field": ParagraphStyle("field", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=16, textColor=INK, leading=19, spaceAfter=2),
        "loc": ParagraphStyle("loc", parent=base["Normal"], fontName="Helvetica",
                              fontSize=10, textColor=MUTED, leading=13),
        "desc": ParagraphStyle("desc", parent=base["Normal"], fontName="Helvetica",
                               fontSize=9, textColor=colors.HexColor("#33443A"), leading=12,
                               spaceBefore=6),
        "section": ParagraphStyle("section", parent=base["Normal"], fontName="Helvetica-Bold",
                                  fontSize=8.5, textColor=MUTED, leading=11, spaceBefore=4),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica",
                               fontSize=8.5, textColor=INK, leading=11),
        "cellk": ParagraphStyle("cellk", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, textColor=MUTED, leading=11),
        "cellv": ParagraphStyle("cellv", parent=base["Normal"], fontName="Helvetica",
                                fontSize=9, textColor=INK, leading=11),
        "statk": ParagraphStyle("statk", parent=base["Normal"], fontName="Helvetica",
                                fontSize=7.5, textColor=MUTED, leading=9),
        "statv": ParagraphStyle("statv", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=13, textColor=INK, leading=15),
        "mono": ParagraphStyle("mono", parent=base["Normal"], fontName="Courier",
                               fontSize=7.5, textColor=INK, leading=10, wordWrap="CJK"),
        "caption": ParagraphStyle("caption", parent=base["Normal"], fontName="Helvetica-Oblique",
                                  fontSize=7.5, textColor=MUTED, leading=9.5, spaceBefore=4),
        "note": ParagraphStyle("note", parent=base["Normal"], fontName="Helvetica",
                               fontSize=8, textColor=MUTED, leading=11),
    }


def _stat_cells(observations: list[dict]) -> list[tuple[str, str, str]]:
    usable = [o for o in observations if o.get("satellite_usable") and o.get("ndvi_mean_x1000") is not None]
    means = [o["ndvi_mean_x1000"] / 1000 for o in usable]
    precip = [o["precip_mm_x10"] for o in observations if o.get("precip_mm_x10") is not None]
    mean = sum(means) / len(means) if means else None
    maximum = max(means) if means else None
    total_precip = sum(precip) / 10 if precip else None
    return [
        ("OBSERVACIONES", str(len(observations)), f"{len(usable)} con satélite usable"),
        ("NDVI PROMEDIO", f"{mean:.3f}" if mean is not None else "—", "sobre escenas usables"),
        ("NDVI MÁXIMO", f"{maximum:.3f}" if maximum is not None else "—", "pico de vigor"),
        ("LLUVIA ACUMULADA", f"{total_precip:.1f} mm" if total_precip is not None else "—", "en el período"),
    ]


def render_certification_pdf(document: CertificationDocumentResponse) -> bytes:
    """Compone el PDF del certificado y devuelve sus bytes."""
    styles = _styles()
    field = document.field
    snapshot = document.snapshot or {}
    observations = sorted(snapshot.get("observations", []), key=lambda o: o.get("date", ""))
    sources = snapshot.get("sources", [])
    anchor = document.anchor

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Certificado TERRIA {document.cert_uid}",
        author="TERRIA",
        subject="Certificado de trazabilidad de campos",
    )
    width = doc.width
    story: list = []

    # ── Encabezado ────────────────────────────────────────────────────────────
    status = document.verification_status
    badge = Table(
        [[Paragraph(f"<b>{STATUS_LABEL.get(status, status.upper())}</b>",
                    ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=colors.white, leading=11))]],
        colWidths=[42 * mm],
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), STATUS_COLOR.get(status, MUTED)),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    right = [
        Paragraph("Certificado de trazabilidad", styles["doctitle"]),
        Paragraph(f"Certificado {document.cert_uid[:8]} · V{document.version}", styles["loc"]),
        Spacer(1, 4),
        badge,
    ]
    header = Table(
        [[[Paragraph("TERRIA", styles["brand"]),
           Paragraph("Trazabilidad verificable de la tierra", styles["tag"])], right]],
        colWidths=[width * 0.55, width * 0.45],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 2, BRAND),
    ]))
    story.append(header)
    story.append(Spacer(1, 12))

    # ── Campo ─────────────────────────────────────────────────────────────────
    location = ", ".join(x for x in [field.locality, field.province] if x) or "Ubicación no informada"
    story.append(Paragraph(field.name, styles["field"]))
    story.append(Paragraph(location, styles["loc"]))
    if field.description:
        story.append(Paragraph(field.description, styles["desc"]))

    details = [
        [Paragraph("Superficie", styles["cellk"]), Paragraph(f"{field.area_hectares:.2f} ha", styles["cellv"]),
         Paragraph("Jurisdicción", styles["cellk"]), Paragraph(field.province or "—", styles["cellv"])],
        [Paragraph("Período", styles["cellk"]), Paragraph(f"{document.period_from} – {document.period_to}", styles["cellv"]),
         Paragraph("Versión", styles["cellk"]), Paragraph(f"V{document.version}", styles["cellv"])],
        [Paragraph("Emitido", styles["cellk"]),
         Paragraph(_date((document.issued_at or document.created_at).isoformat()), styles["cellv"]),
         Paragraph("Certificado", styles["cellk"]),
         Paragraph(f"<font face='Courier' size='7.5'>{document.cert_uid}</font>", styles["cellv"])],
    ]
    details_table = Table(details, colWidths=[width * 0.16, width * 0.34, width * 0.16, width * 0.34])
    details_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
    ]))
    story.append(Spacer(1, 8))
    story.append(details_table)

    # ── Resumen ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(Paragraph("RESUMEN DEL HISTORIAL CERTIFICADO", styles["section"]))
    stats = _stat_cells(observations)
    stat_row = [[Paragraph(k, styles["statk"]) for k, _, _ in stats],
                [Paragraph(v, styles["statv"]) for _, v, _ in stats],
                [Paragraph(s, styles["statk"]) for _, _, s in stats]]
    stat_table = Table(stat_row, colWidths=[width / 4] * 4)
    stat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(Spacer(1, 6))
    story.append(stat_table)

    # ── Observaciones ─────────────────────────────────────────────────────────
    if observations:
        story.append(Spacer(1, 12))
        story.append(Paragraph("OBSERVACIONES FECHADAS", styles["section"]))
        head = ["Fecha", "NDVI", "p10", "p90", "Lluvia", "7d", "T mín", "T máx", "Satélite"]
        rows = [[Paragraph(f"<b>{h}</b>", styles["statk"]) for h in head]]
        for o in observations:
            rows.append([
                Paragraph(_date(o.get("date")), styles["body"]),
                Paragraph(_num(o.get("ndvi_mean_x1000"), 1000, 3), styles["body"]),
                Paragraph(_num(o.get("ndvi_p10_x1000"), 1000, 3), styles["body"]),
                Paragraph(_num(o.get("ndvi_p90_x1000"), 1000, 3), styles["body"]),
                Paragraph(_num(o.get("precip_mm_x10"), 10, 1), styles["body"]),
                Paragraph(_num(o.get("precip_7d_mm_x10"), 10, 1), styles["body"]),
                Paragraph(_num(o.get("temp_min_c_x10"), 10, 1), styles["body"]),
                Paragraph(_num(o.get("temp_max_c_x10"), 10, 1), styles["body"]),
                Paragraph("usable" if o.get("satellite_usable") else "descartada", styles["body"]),
            ])
        obs_table = Table(rows, colWidths=[width * w for w in (0.17, 0.11, 0.09, 0.09, 0.11, 0.09, 0.09, 0.09, 0.16)],
                          repeatRows=1)
        obs_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAF8")]),
        ]))
        story.append(Spacer(1, 6))
        story.append(obs_table)

    # ── Seguimiento mensual ───────────────────────────────────────────────────
    monthly = snapshot.get("monthly", [])
    if monthly:
        story.append(Spacer(1, 12))
        story.append(Paragraph("SEGUIMIENTO MENSUAL", styles["section"]))
        head = ["Mes", "Campaña", "Escenas", "NDVI", "NDVI máx", "Lluvia", "T media"]
        rows = [[Paragraph(f"<b>{label}</b>", styles["statk"]) for label in head]]
        for item in monthly:
            rows.append([
                Paragraph(item.get("month", "—"), styles["body"]),
                Paragraph(item.get("campaign", "—"), styles["body"]),
                Paragraph(
                    f"{item.get('usable_scenes', 0)} / {item.get('satellite_scenes', 0)}",
                    styles["body"],
                ),
                Paragraph(_num(item.get("ndvi_mean_x1000"), 1000, 3), styles["body"]),
                Paragraph(_num(item.get("ndvi_max_x1000"), 1000, 3), styles["body"]),
                Paragraph(_num(item.get("precip_mm_x10"), 10, 1), styles["body"]),
                Paragraph(_num(item.get("temp_mean_c_x10"), 10, 1), styles["body"]),
            ])
        monthly_table = Table(
            rows,
            colWidths=[width * w for w in (0.14, 0.15, 0.15, 0.13, 0.14, 0.14, 0.15)],
            repeatRows=1,
        )
        monthly_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAF8")]),
        ]))
        story.append(Spacer(1, 6))
        story.append(monthly_table)

    # ── Fuentes ───────────────────────────────────────────────────────────────
    if sources:
        story.append(Spacer(1, 12))
        story.append(Paragraph("FUENTES DE DATOS", styles["section"]))
        rows = [[Paragraph(f"<b>{s.get('provider', s.get('id', ''))}</b>", styles["cellk"]),
                 Paragraph(
                     f"{s.get('dataset', '')} · obtenida {_date(s.get('retrieved_at'))}",
                     styles["cellv"])] for s in sources]
        sources_table = Table(rows, colWidths=[width * 0.3, width * 0.7])
        sources_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ]))
        story.append(Spacer(1, 6))
        story.append(sources_table)

    # ── Integridad ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    story.append(Paragraph("INTEGRIDAD Y ANCLAJE ON-CHAIN", styles["section"]))
    tx = anchor.tx_signature if anchor else None
    explorer = anchor.explorer_url if anchor else None
    tx_cell = Paragraph(f"<link href='{explorer}'>{tx}</link>", styles["mono"]) if explorer and tx else _tx_paragraph(tx, styles)
    integrity_rows = [
        [Paragraph("Hash del contenido", styles["cellk"]), Paragraph(document.content_hash, styles["mono"])],
        [Paragraph("Hash versión anterior", styles["cellk"]),
         Paragraph(document.prev_content_hash or "— (primera versión)", styles["mono"])],
        [Paragraph("Memo on-chain", styles["cellk"]),
         Paragraph(anchor.memo_payload if anchor else "—", styles["mono"])],
        [Paragraph("Red", styles["cellk"]), Paragraph(anchor.cluster if anchor else "—", styles["cellv"])],
        [Paragraph("Transacción", styles["cellk"]), tx_cell],
        [Paragraph("Algoritmo", styles["cellk"]),
         Paragraph(f"{document.algorithm_version} · {document.schema_version}", styles["cellv"])],
    ]
    integrity_table = Table(integrity_rows, colWidths=[width * 0.26, width * 0.74])
    integrity_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
    ]))
    story.append(Spacer(1, 6))
    story.append(integrity_table)

    # ── Nota ──────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 12))
    note = Table([[Paragraph(
        "La blockchain prueba <b>existencia e integridad</b> del registro certificado: que existía en una "
        "fecha y que no fue alterado desde entonces. No certifica por sí misma la veracidad del dato agronómico.",
        styles["note"])]], colWidths=[width])
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, BRAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(note)

    doc.build(story)
    return buffer.getvalue()


def _tx_paragraph(tx: str | None, styles: dict) -> Paragraph:
    return Paragraph(tx or "sin ancla pública (modo local)", styles["mono"])
