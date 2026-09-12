"""Aislamiento de tests: las pruebas corren siempre contra SQLite temporal.

Se ejecuta antes de que los módulos de test importen `app.*`: limpia las URLs de
Supabase (que pueden venir del `.env` local) y apunta `TERRIA_DB_PATH` a un
archivo descartable. El test de integración real con Supabase vive en
`test_supabase_backend.py` y requiere `TERRIA_TEST_SUPABASE=1`.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

os.environ["DATABASE_URL"] = ""
os.environ["DATABASE_DIRECT_URL"] = ""
os.environ["MIGRATION_DATABASE_URL"] = ""

_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="terria-tests-"))
os.environ["TERRIA_DB_PATH"] = str(_TEST_DB_DIR / "terria.db")
os.environ["TIMELAPSE_STORAGE_DIR"] = str(_TEST_DB_DIR / "storage")
