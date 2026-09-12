from __future__ import annotations

import httpx

from app.config import settings


class SupabasePayloadStorage:
    """Guarda los bytes canónicos del snapshot en Supabase Storage.

    La base solo conserva la referencia (`cert.payloads.storage_ref`), nunca los
    bytes: la verificación los descarga y recomputa el hash.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        service_key: str | None = None,
        bucket: str | None = None,
    ) -> None:
        self._base = (base_url or settings.supabase_url or "").rstrip("/")
        self._key = service_key or settings.supabase_service_role_key or ""
        self._bucket = bucket or settings.cert_storage_bucket
        if not self._base or not self._key:
            raise RuntimeError("Supabase Storage requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        self._headers = {"Authorization": f"Bearer {self._key}", "apikey": self._key}

    def _ensure_bucket(self) -> None:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{self._base}/storage/v1/bucket",
                headers={**self._headers, "Content-Type": "application/json"},
                json={"name": self._bucket, "public": False},
            )
        if response.status_code in (200, 201, 409):
            return
        if response.status_code == 400 and "exist" in response.text.lower():
            return
        response.raise_for_status()

    def upload(self, path: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self._ensure_bucket()
        storage_ref = f"{self._bucket}/{path}"
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self._base}/storage/v1/object/{storage_ref}",
                headers={**self._headers, "Content-Type": content_type, "x-upsert": "true"},
                content=data,
            )
            response.raise_for_status()
        return storage_ref

    def download(self, storage_ref: str) -> bytes | None:
        with httpx.Client(timeout=60) as client:
            response = client.get(
                f"{self._base}/storage/v1/object/{storage_ref}", headers=self._headers
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.content
