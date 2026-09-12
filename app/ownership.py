"""Resolución del `owner_id` requerido por `core.fields` (FK a `auth.users`).

Mientras el MVP no tenga Auth por request, las escrituras del backend usan un
owner de sistema: `TERRIA_DEFAULT_OWNER_ID` si está configurado, o un usuario
de Auth provisionado on-demand con la GoTrue Admin API (service role, sólo
backend). El UUID se cachea en proceso.
"""

from __future__ import annotations

import logging
import secrets
from uuid import UUID

import httpx
from sqlalchemy.dialects import postgresql

from app.config import settings
from app.db import get_engine
from app.models import profiles

logger = logging.getLogger(__name__)

_cached_owner_id: UUID | None = None


def resolve_owner_id() -> UUID:
    global _cached_owner_id
    if settings.terria_default_owner_id:
        return UUID(settings.terria_default_owner_id)
    if _cached_owner_id is None:
        _cached_owner_id = _provision_system_user()
    return _cached_owner_id


def reset_owner_cache() -> None:
    global _cached_owner_id
    _cached_owner_id = None


def _admin_headers() -> dict[str, str]:
    key = settings.supabase_service_role_key or ""
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _provision_system_user() -> UUID:
    if not (settings.supabase_url and settings.supabase_service_role_key):
        raise RuntimeError(
            "Sin owner para escrituras en Supabase: definí TERRIA_DEFAULT_OWNER_ID "
            "o SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY para auto-provisionar el "
            "usuario de sistema."
        )

    email = settings.terria_system_email
    base = (settings.supabase_url or "").rstrip("/")
    with httpx.Client(timeout=15) as client:
        res = client.post(
            f"{base}/auth/v1/admin/users",
            headers=_admin_headers(),
            json={
                "email": email,
                "password": secrets.token_urlsafe(24),
                "email_confirm": True,
                "user_metadata": {"kind": "system"},
            },
        )
        if res.status_code in (200, 201):
            user_id = UUID(res.json()["id"])
        elif res.status_code in (409, 422):
            user_id = _find_user_by_email(client, base, email)
        else:
            raise RuntimeError(
                f"GoTrue admin create_user falló: {res.status_code} {res.text[:200]}"
            )

    with get_engine().begin() as conn:
        conn.execute(
            postgresql.insert(profiles)
            .values(id=user_id, display_name="TERRIA System")
            .on_conflict_do_nothing(index_elements=["id"])
        )
    logger.info("Owner de sistema resuelto: %s (%s)", email, user_id)
    return user_id


def _find_user_by_email(client: httpx.Client, base: str, email: str) -> UUID:
    res = client.get(
        f"{base}/auth/v1/admin/users",
        headers=_admin_headers(),
        params={"page": 1, "per_page": 200},
    )
    res.raise_for_status()
    data = res.json()
    users = data.get("users", []) if isinstance(data, dict) else data
    for user in users:
        if user.get("email") == email:
            return UUID(user["id"])
    raise RuntimeError(f"Usuario de sistema {email} no encontrado tras conflicto de alta")
