from __future__ import annotations

MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"
MEMO_PREFIX = "TERRIA1"
FORMAT_VERSION = "v1"
EMPTY_PREV = "-"


def build_memo(cert_uid: str, content_hash_hex: str, prev_hash_hex: str | None = None) -> str:
    """On-chain payload: TERRIA1|v1|<cert_uid>|<content_hash_hex>|<prev_hash_hex|->"""
    if "|" in cert_uid:
        raise ValueError("cert_uid must not contain '|'")
    if len(content_hash_hex) != 64:
        raise ValueError("content_hash must be a 64-char SHA-256 hex digest")
    previous = prev_hash_hex or EMPTY_PREV
    if previous != EMPTY_PREV and len(previous) != 64:
        raise ValueError("prev_hash must be a 64-char SHA-256 hex digest or '-'")
    return "|".join([MEMO_PREFIX, FORMAT_VERSION, cert_uid, content_hash_hex, previous])


def parse_memo(text: str) -> dict[str, str | None]:
    parts = text.split("|")
    if len(parts) != 5 or parts[0] != MEMO_PREFIX:
        raise ValueError(f"invalid TERRIA memo: {text!r}")
    _, version, cert_uid, content_hash_hex, previous = parts
    return {
        "format_version": version,
        "cert_uid": cert_uid,
        "content_hash": content_hash_hex,
        "prev_hash": None if previous == EMPTY_PREV else previous,
    }
