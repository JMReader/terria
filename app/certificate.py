from __future__ import annotations

import hashlib
import json
import unicodedata

from app.schemas import FieldResponse, utcnow


def field_content_hash(field: FieldResponse) -> str:
    """SHA-256 over the canonical field payload (stable key order).

    This is the same identifier the frontend shows in the passport's
    Certificado section and the one printed on the blockchain PDF.
    """
    canonical = json.dumps(
        {
            "id": str(field.id),
            "name": field.name,
            "boundary": field.boundary.model_dump(),
            "area_hectares": field.area_hectares,
            "province": field.province,
            "locality": field.locality,
            "visibility": field.visibility,
            "public_slug": field.public_slug,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ascii(text: str) -> str:
    """PDF core fonts are WinAnsi — strip accents to keep the hand-rolled file simple."""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "replace").decode("ascii")


def _esc(text: str) -> str:
    return _ascii(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_certificate_pdf(field: FieldResponse, passport_url: str | None) -> bytes:
    """Minimal single-page PDF 1.4 certificate — no external dependencies."""
    content_hash = field_content_hash(field)
    issued = utcnow().strftime("%Y-%m-%d %H:%M UTC")
    location = ", ".join(p for p in (field.locality, field.province, field.country) if p)

    lines: list[tuple[str, int, int, int]] = [
        ("TERRIA", 26, 60, 780),
        ("Certificado Blockchain de Parcela", 15, 60, 748),  # fmt: skip
        (_esc(field.name), 20, 60, 700),
        (f"Localizacion: {_esc(location or 'Argentina')}", 11, 60, 668),
        (f"Superficie: {field.area_hectares} ha", 11, 60, 650),
        (f"ID de parcela: {field.id}", 11, 60, 620),
        (f"Estado de publicacion: {'Publica' if field.visibility == 'public' else 'Privada'}", 11, 60, 602),
        (f"Emitido: {issued}", 11, 60, 584),
        ("Huella de contenido (SHA-256, payload canonico):", 11, 60, 548),
        (content_hash, 9, 60, 532),
    ]
    if passport_url:
        lines += [
            ("Pasaporte digital (vista viva y verificable):", 11, 60, 496),
            (_esc(passport_url), 10, 60, 480),
        ]
    lines += [
        ("Este documento acompana la evidencia on-chain registrada por TERRIA.", 10, 60, 440),
        ("Verificacion: la URL publica muestra el mismo hash y la serie agronomica.", 10, 60, 426),
        ("terria — gemelo digital territorial", 9, 60, 80),
    ]

    stream_parts = []
    for text, size, x, y in lines:
        font = "F1" if size >= 15 else "F2"
        stream_parts.append(f"BT /{font} {size} Tf {x} {y} Td ({_ascii(text)}) Tj ET")
    # Hairline separators
    stream_parts.append("60 730 m 535 730 l S")
    stream_parts.append("60 560 m 535 560 l S")
    stream_parts.append("0.2 w")
    content = _ascii("\n".join(stream_parts)).encode("ascii")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF"
    ).encode()
    return bytes(pdf)
