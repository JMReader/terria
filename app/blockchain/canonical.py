from __future__ import annotations

import hashlib
from typing import Any

import rfc8785


class CanonicalizationError(ValueError):
    """The snapshot contains values that would make the hash non-deterministic."""


def _reject_floats(value: Any) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, float):
        raise CanonicalizationError(
            "floats are not allowed: use scaled integers or decimal strings"
        )
    if isinstance(value, (int, str)):
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalizationError("snapshot object keys must be strings")
            _reject_floats(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _reject_floats(item)
        return
    raise CanonicalizationError(f"value of type {type(value)!r} cannot be canonicalized")


def canonical_bytes(document: Any) -> bytes:
    """Serialize to JCS (RFC 8785): sorted keys, no whitespace, UTF-8."""
    _reject_floats(document)
    return rfc8785.dumps(document)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(document: Any) -> str:
    raw = bytes(document) if isinstance(document, (bytes, bytearray)) else canonical_bytes(document)
    return sha256_hex(raw)
