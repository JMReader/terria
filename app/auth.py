"""Auth de dueños del pasaporte digital — modo dual.

Con Supabase configurado (`settings.use_supabase` + `SUPABASE_URL`/`SUPABASE_ANON_KEY`)
las cuentas viven en GoTrue (`auth.users`) y el Bearer token es el access_token JWT
— así `owner_id` de `core.fields` (FK a `auth.users`) matchea directo.

Sin Supabase (dev local / tests), cae a un store SQLite con PBKDF2 y tokens
opacos, mismo contrato de API.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import settings
from app.schemas import utcnow

PBKDF2_ITERATIONS = 120_000


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    email: Annotated[str, Field(min_length=3, max_length=254)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    name: Annotated[str | None, Field(max_length=120)] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        local, _, domain = value.partition("@")
        if not local or not domain or "." not in domain:
            raise ValueError("Invalid email address")
        return value


class LoginRequest(StrictModel):
    email: str
    password: str


class OwnerResponse(StrictModel):
    id: UUID
    email: str
    name: str | None
    created_at: datetime


class AuthResponse(StrictModel):
    token: str
    owner: OwnerResponse


class EmailTaken(Exception):
    pass


class InvalidCredentials(Exception):
    pass


# ── Modo Supabase (GoTrue) ────────────────────────────────────────────────────


class _GoTrueAuth:
    """Cliente mínimo de GoTrue sobre httpx — cuentas reales en auth.users."""

    def __init__(self) -> None:
        self.base = settings.supabase_url.rstrip("/") + "/auth/v1"  # type: ignore[union-attr]
        self.anon_key = settings.supabase_anon_key or ""
        self.service_key = settings.supabase_service_role_key or self.anon_key

    def _headers(self, key: str | None = None, token: str | None = None) -> dict[str, str]:
        headers = {"apikey": key or self.anon_key, "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _to_owner(user: dict[str, Any]) -> OwnerResponse:
        metadata = user.get("user_metadata") or {}
        created = user.get("created_at") or utcnow().isoformat()
        return OwnerResponse(
            id=UUID(user["id"]),
            email=user["email"],
            name=metadata.get("name"),
            created_at=datetime.fromisoformat(str(created).replace("Z", "+00:00")),
        )

    def _password_grant(self, email: str, password: str) -> AuthResponse:
        resp = httpx.post(
            f"{self.base}/token?grant_type=password",
            headers=self._headers(),
            json={"email": email, "password": password},
            timeout=10,
        )
        if resp.status_code != 200:
            raise InvalidCredentials
        data = resp.json()
        return AuthResponse(
            token=data["access_token"], owner=self._to_owner(data["user"])
        )

    def register(self, payload: RegisterRequest) -> AuthResponse:
        if settings.supabase_service_role_key:
            # Admin API: crea el usuario ya confirmado (evita el flujo de e-mail).
            resp = httpx.post(
                f"{self.base}/admin/users",
                headers=self._headers(key=self.service_key),
                json={
                    "email": payload.email,
                    "password": payload.password,
                    "email_confirm": True,
                    "user_metadata": {"name": payload.name} if payload.name else {},
                },
                timeout=10,
            )
            if resp.status_code == 422 or (
                resp.status_code == 400 and "already" in resp.text.lower()
            ):
                raise EmailTaken
            if resp.status_code not in (200, 201):
                raise InvalidCredentials
        else:
            resp = httpx.post(
                f"{self.base}/signup",
                headers=self._headers(),
                json={
                    "email": payload.email,
                    "password": payload.password,
                    "data": {"name": payload.name} if payload.name else {},
                },
                timeout=10,
            )
            if resp.status_code == 422 or (
                resp.status_code == 400 and "already" in resp.text.lower()
            ):
                raise EmailTaken
            if resp.status_code != 200:
                raise InvalidCredentials
            data = resp.json()
            if data.get("access_token"):
                return AuthResponse(
                    token=data["access_token"], owner=self._to_owner(data["user"])
                )
        return self._password_grant(payload.email, payload.password)

    def login(self, payload: LoginRequest) -> AuthResponse:
        return self._password_grant(payload.email.strip().lower(), payload.password)

    def logout(self, token: str) -> None:
        try:
            httpx.post(
                f"{self.base}/logout",
                headers=self._headers(token=token),
                timeout=10,
            )
        except httpx.HTTPError:
            pass  # best-effort: el access_token expira solo

    def owner_for_token(self, token: str | None) -> OwnerResponse | None:
        if not token:
            return None
        try:
            resp = httpx.get(
                f"{self.base}/user",
                headers=self._headers(token=token),
                timeout=10,
            )
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        try:
            return self._to_owner(resp.json())
        except (KeyError, ValueError):
            return None


# ── Modo local (SQLite + PBKDF2) ──────────────────────────────────────────────


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


class _LocalAuthStore:
    """SQLite-backed owner accounts and opaque bearer tokens (dev sin Supabase)."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = str(db_path if db_path is not None else settings.db_file_path)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS owners (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT,
                created_at TEXT NOT NULL
            );
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_tokens (
                token TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """)

    def register(self, payload: RegisterRequest) -> AuthResponse:
        owner = OwnerResponse(
            id=uuid4(),
            email=payload.email,
            name=payload.name,
            created_at=utcnow(),
        )
        with self._get_connection() as conn:
            existing = conn.execute(
                "SELECT id FROM owners WHERE email = ?", (owner.email,)
            ).fetchone()
            if existing:
                raise EmailTaken
            conn.execute(
                "INSERT INTO owners (id, email, password_hash, name, created_at) VALUES (?, ?, ?, ?, ?)",
                (
                    str(owner.id),
                    owner.email,
                    _hash_password(payload.password),
                    owner.name,
                    owner.created_at.isoformat(),
                ),
            )
        return AuthResponse(token=self._issue_token(owner.id), owner=owner)

    def login(self, payload: LoginRequest) -> AuthResponse:
        email = payload.email.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM owners WHERE email = ?", (email,)
            ).fetchone()
        if not row or not _verify_password(payload.password, row["password_hash"]):
            raise InvalidCredentials
        owner = self._row_to_owner(row)
        return AuthResponse(token=self._issue_token(owner.id), owner=owner)

    def logout(self, token: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))

    def owner_for_token(self, token: str | None) -> OwnerResponse | None:
        if not token:
            return None
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT o.* FROM owners o
                JOIN auth_tokens t ON t.owner_id = o.id
                WHERE t.token = ?
                """,
                (token,),
            ).fetchone()
        return self._row_to_owner(row) if row else None

    def _issue_token(self, owner_id: UUID) -> str:
        token = secrets.token_urlsafe(32)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO auth_tokens (token, owner_id, created_at) VALUES (?, ?, ?)",
                (token, str(owner_id), utcnow().isoformat()),
            )
        return token

    @staticmethod
    def _row_to_owner(row: sqlite3.Row) -> OwnerResponse:
        return OwnerResponse(
            id=UUID(row["id"]),
            email=row["email"],
            name=row["name"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


# ── Facade: elige el backend según la config ──────────────────────────────────


class _AuthFacade:
    """Despacha a GoTrue (Supabase) o al store local según `settings.use_supabase`.

    Lazy: nunca crea el archivo SQLite cuando Supabase está activo (el FS de
    Vercel es read-only fuera de /tmp).
    """

    def __init__(self) -> None:
        self._local: _LocalAuthStore | None = None
        self._gotrue: _GoTrueAuth | None = None

    @property
    def _use_gotrue(self) -> bool:
        return bool(
            settings.use_supabase
            and settings.supabase_url
            and settings.supabase_anon_key
        )

    @property
    def _backend(self) -> _GoTrueAuth | _LocalAuthStore:
        if self._use_gotrue:
            if self._gotrue is None:
                self._gotrue = _GoTrueAuth()
            return self._gotrue
        if self._local is None:
            self._local = _LocalAuthStore()
        return self._local

    def register(self, payload: RegisterRequest) -> AuthResponse:
        return self._backend.register(payload)

    def login(self, payload: LoginRequest) -> AuthResponse:
        return self._backend.login(payload)

    def logout(self, token: str) -> None:
        self._backend.logout(token)

    def owner_for_token(self, token: str | None) -> OwnerResponse | None:
        return self._backend.owner_for_token(token)


auth_store = _AuthFacade()


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        token = header[len("Bearer ") :].strip()
        return token or None
    return None


def unauthorized(request: Request) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "A valid owner session is required",
            "request_id": request.headers.get("X-Request-ID", "local"),
        },
    )


def get_current_owner(request: Request) -> OwnerResponse:
    owner = auth_store.owner_for_token(bearer_token(request))
    if owner is None:
        raise unauthorized(request) from None
    return owner


def get_optional_owner(request: Request) -> OwnerResponse | None:
    return auth_store.owner_for_token(bearer_token(request))
