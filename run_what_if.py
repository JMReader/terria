#!/usr/bin/env python3
"""Lanzador interactivo del Optimizador Multicultivo What-If (TERRIA Agro Intelligence).

Uso directo en terminal de VS Code:
  python run_what_if.py
  uv run python run_what_if.py
"""
import sys
from app.what_if.cli import main

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("-i")
    main()
