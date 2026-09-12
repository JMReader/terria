"""Genera el PDF de una certificación TERRIA en disco.

Uso:
    uv run python scripts/generate_certificate_pdf.py <cert_uid>
    uv run python scripts/generate_certificate_pdf.py <cert_uid> --output ~/Desktop/x.pdf

Por defecto deja el archivo en ~/Desktop/certificado-terria-<cert_uid>.pdf.
No necesita navegador: compone el PDF con ReportLab.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.blockchain.pdf import render_certification_pdf
from app.blockchain.service import build_certification_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el PDF de una certificación TERRIA.")
    parser.add_argument("cert_uid", help="UID del certificado (GET /cert/{cert_uid})")
    parser.add_argument("--output", default=None, help="Ruta del PDF de salida")
    args = parser.parse_args()

    document = build_certification_document(args.cert_uid)
    if document is None:
        raise SystemExit(f"No existe la certificación {args.cert_uid}")

    if args.output:
        output = Path(args.output).expanduser()
    else:
        desktop = Path.home() / "Desktop"
        base = desktop if desktop.exists() else Path.home()
        output = base / f"certificado-terria-{document.cert_uid}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)

    output.write_bytes(render_certification_pdf(document))
    print(f"PDF generado: {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
