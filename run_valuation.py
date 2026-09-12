#!/usr/bin/env python3
"""Lanzador interactivo del Proyector de Valor de Tierra a Futuro (TERRIA FinTech & Real Estate).

Uso:
  python run_valuation.py
  uv run python run_valuation.py
"""
import sys
from app.valuation.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("-i")
    main()
