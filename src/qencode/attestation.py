"""
Signed certification receipts (option B).

This module provides:
- issuing Ed25519-signed receipts (server-side, private key)
- verifying receipts (public key)
- helper to decide whether "official certified" is required

Design:
- receipts live inside entry JSON under entry["trust"]["receipt"]
- "official certified" is granted only if the receipt signature verifies
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KEYS_DIR = _REPO_ROOT / "keys"
_PUBLIC_KEY_PATH = _KEYS_DIR / "qencode_ed25519_public.pem"

_ENV_PRIVATE_KEY_PEM = "QENCODE_SIGNING_PRIVATE_KEY_PEM"
_ENV_REQUIRE_OFFICIAL = "QENCODE_REQUIRE_OFFICIAL_RECEIPTS"


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def require_official_receipts() -> bool:
    v = (os.environ.get(_ENV_REQUIRE_OFFICIAL) or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _private_key_from_env() -> Optional[Ed25519PrivateKey]:
    pem = os.environ.get(_ENV_PRIVATE_KEY_PEM)
    if not pem:
        return None
    pem_bytes = pem.encode("utf-8") if isinstance(pem, str) else pem
    key = serialization.load_pem_private_key(pem_bytes, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Loaded private key is not Ed25519")
    return key


def _load_public_key_from_file() -> Optional[Ed25519PublicKey]:
    if not _PUBLIC_KEY_PATH.exists():
        return None
    data = _PUBLIC_KEY_PATH.read_bytes()
    key = serialization.load_pem_public_key(data)
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError("Loaded public key is not Ed25519")
    return key


def get_public_key() -> Tuple[Optional[Ed25519PublicKey], str]:
    """
    Returns (public_key, reason_string).
    public_key is None when no key is available for verification.
    """
    pub = _load_public_key_from_file()
    if pub is not None:
        return pub, f"loaded public key from {_PUBLIC_KEY_PATH}"

    priv = _private_key_from_env()
    if priv is not None:
        return priv.public_key(), "derived public key from env private key"

    return None, "no public key available"


def _encode_sig(sig: bytes) -> str:
    return base64.b64encode(sig).decode("ascii")


def _decode_sig(sig_b64: str) -> bytes:
    return base64.b64decode(sig_b64.encode("ascii"))


def verify_receipt(payload: Dict[str, Any], signature_b64: str, *, entry: Dict[str, Any]) -> Tuple[bool, str]:
    pub, reason = get_public_key()
    if pub is None:
        return False, f"cannot verify receipt: {reason}"

    canonical = _canonical_json_bytes(payload)
    try:
        sig = _decode_sig(signature_b64)
        pub.verify(sig, canonical)
        return True, "signature verified"
    except InvalidSignature:
        return False, "invalid signature"
    except Exception as e:
        return False, f"verification error: {e}"


def _entry_hash_sha256(entry: Dict[str, Any]) -> Optional[str]:
    prov = entry.get("provenance") or {}
    h = prov.get("entry_hash_sha256")
    return str(h) if h is not None else None


def issue_receipt(
    *,
    entry: Dict[str, Any],
    suite_version: str,
    leaderboard_rules_version: str = "v1",
    certified_at_utc: Optional[str] = None,
    receipt_version: str = "1.0",
) -> Dict[str, Any]:
    """
    Issue a signed receipt for a single certified entry.

    Requires env var `QENCODE_SIGNING_PRIVATE_KEY_PEM`.
    """
    priv = _private_key_from_env()
    if priv is None:
        raise RuntimeError(
            f"Missing signing key. Set env var {_ENV_PRIVATE_KEY_PEM} to your Ed25519 private key (PEM)."
        )

    if not certified_at_utc:
        certified_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry_id = entry.get("entry_id") or "unknown_entry"
    entry_hash = _entry_hash_sha256(entry)
    if not entry_hash:
        raise RuntimeError("Entry missing provenance.entry_hash_sha256; cannot issue receipt reliably.")

    payload: Dict[str, Any] = {
        "receipt_version": receipt_version,
        "issued_at_utc": certified_at_utc,
        "issued_by": "qencode",
        "suite_version": suite_version,
        "leaderboard_rules_version": leaderboard_rules_version,
        "entry_id": entry_id,
        "entry_hash_sha256": entry_hash,
        "trust_level": "certified",
    }

    canonical = _canonical_json_bytes(payload)
    signature = priv.sign(canonical)
    receipt = {
        "payload": payload,
        "signature": _encode_sig(signature),
        "signature_algorithm": "ed25519",
    }

    return receipt


def ensure_public_key_written() -> Optional[Path]:
    """
    If signing private key is available, write derived public key to repo keys/.
    Returns the written path if successful, else None.
    """
    if _PUBLIC_KEY_PATH.exists():
        return _PUBLIC_KEY_PATH
    priv = _private_key_from_env()
    if priv is None:
        return None
    _KEYS_DIR.mkdir(parents=True, exist_ok=True)
    pub = priv.public_key()
    pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _PUBLIC_KEY_PATH.write_bytes(pem)
    return _PUBLIC_KEY_PATH


def receipt_from_entry(entry: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns (receipt_dict, error_message).
    receipt_dict is the raw trust.receipt object, if present.
    """
    trust = entry.get("trust") or {}
    receipt = trust.get("receipt")
    if receipt is None:
        return None, "entry has no trust.receipt"
    if not isinstance(receipt, dict):
        return None, "entry trust.receipt is not an object"
    payload = receipt.get("payload")
    sig = receipt.get("signature")
    if not isinstance(payload, dict) or not isinstance(sig, str):
        return None, "receipt missing payload/signature"
    return receipt, None


def verify_entry_receipt(entry: Dict[str, Any]) -> Tuple[bool, str]:
    receipt, err = receipt_from_entry(entry)
    if receipt is None:
        return False, err or "receipt missing"

    payload = receipt.get("payload") or {}
    sig_b64 = receipt.get("signature")

    entry_hash = _entry_hash_sha256(entry)
    if not entry_hash:
        return False, "entry missing provenance.entry_hash_sha256"

    if payload.get("entry_hash_sha256") != entry_hash:
        return False, "receipt payload entry_hash mismatch"

    return verify_receipt(payload, sig_b64, entry=entry)

