from __future__ import annotations

import base64
import binascii
import json

from solders.keypair import Keypair


def load_issuer(secret_key: str | None) -> Keypair:
    """Load the issuer keypair from a JSON byte array, base58 string, or base64 secret.

    With no secret configured it returns an ephemeral keypair, which is only safe for
    the local in-memory anchor provider used in development and tests.
    """
    if not secret_key:
        return Keypair()

    value = secret_key.strip()

    try:
        data = json.loads(value)
    except ValueError:
        data = None
    if isinstance(data, list):
        return Keypair.from_bytes(bytes(data))

    try:
        return Keypair.from_base58_string(value)
    except Exception:  # noqa: BLE001 - fall through to base64 encodings
        pass

    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("SOLANA_ISSUER_SECRET_KEY is not a valid keypair encoding") from exc

    if len(raw) == 64:
        return Keypair.from_bytes(raw)
    if len(raw) == 32:
        return Keypair.from_seed(raw)
    raise ValueError("SOLANA_ISSUER_SECRET_KEY must decode to 32 or 64 bytes")
