"""Ed25519 signatures over entry content hashes.

What is signed
--------------
An entry's ``provenance.entry_hash_sha256`` is a SHA-256 over its canonical JSON with the
volatile fields removed (timestamps, entry_id, git_commit, machine, and the signature
fields themselves). Every energy, gap, setting and the certification tier are inside it.
The project key signs that hash, with a fixed prefix so a signature over an entry hash can
never be mistaken for a signature over anything else:

    message = b"qencode/entry-sha256/v1:" + entry_hash_hex

The signature goes in ``trust.signature_b64`` (base64, 64 bytes) and the key that made it
in ``trust.signing_key_id``. Both are excluded from the hash, so signing an entry changes
neither its hash nor its entry_id.

What a valid signature shows
----------------------------
The content hash is a checksum: anyone can edit an entry and recompute it. A valid
signature under the published key shows the holder of the project's private key signed
exactly this content. It says nothing about whether the computation was right -- that is
what re-running the entry checks.

Keys
----
The public key is published in the repository at ``keys/qencode_ed25519_public.pem``. The
private key never enters the repository: by default it lives at
``~/.qencode/qencode_ed25519_private.pem``, or at the path in ``QENCODE_SIGNING_KEY``. (Not
``~/.qencode/signing_key.pem``: the frozen v3 generator auto-loads a key at that path and
would sign with its own, older recipe.)

The pipeline does not sign. Entries are generated unsigned in the pinned environment and
signed afterwards by scripts/sign_entries.py, so the signing dependency and the key stay
out of the environment that produces results.

Verification uses only the standard library (an implementation of RFC 8032 verification,
checked against the RFC's test vectors in tests/test_signing.py), so anyone can verify a
signature with nothing installed. Signing uses the ``cryptography`` package and is only
ever done by the key holder.
"""
from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Optional, Tuple

MESSAGE_PREFIX = b"qencode/entry-sha256/v1:"

_REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_KEY_PATH = _REPO_ROOT / "keys" / "qencode_ed25519_public.pem"
DEFAULT_PRIVATE_KEY_PATH = Path.home() / ".qencode" / "qencode_ed25519_private.pem"

# DER prefix of an Ed25519 SubjectPublicKeyInfo (RFC 8410): SEQUENCE { SEQUENCE { OID
# 1.3.101.112 }, BIT STRING (32 bytes) }. A PEM public key is this plus the raw key.
_SPKI_ED25519_PREFIX = bytes.fromhex("302a300506032b6570032100")


def message_for(entry_hash_hex: str) -> bytes:
    if len(entry_hash_hex) != 64 or any(c not in "0123456789abcdef" for c in entry_hash_hex):
        raise ValueError(f"not a lowercase SHA-256 hex digest: {entry_hash_hex!r}")
    return MESSAGE_PREFIX + entry_hash_hex.encode("ascii")


def key_id(public_key_raw: bytes) -> str:
    """A short, checkable name for a public key: the first 16 hex digits of its SHA-256."""
    return "ed25519:" + hashlib.sha256(public_key_raw).hexdigest()[:16]


def public_key_from_pem(pem: bytes) -> bytes:
    """The 32 raw bytes of an Ed25519 public key in PEM (SubjectPublicKeyInfo) form."""
    lines = [l.strip() for l in pem.decode("ascii").splitlines()]
    try:
        start = lines.index("-----BEGIN PUBLIC KEY-----")
        end = lines.index("-----END PUBLIC KEY-----")
    except ValueError:
        raise ValueError("not a PEM public key") from None
    der = base64.b64decode("".join(lines[start + 1:end]))
    if len(der) != 44 or not der.startswith(_SPKI_ED25519_PREFIX):
        raise ValueError("not an Ed25519 public key")
    return der[len(_SPKI_ED25519_PREFIX):]


def load_public_key(path: Path = PUBLIC_KEY_PATH) -> Optional[bytes]:
    path = Path(path)
    return public_key_from_pem(path.read_bytes()) if path.exists() else None


# ── RFC 8032 Ed25519 verification, standard library only ─────────────────────
#
# Transcribed from the reference implementation in RFC 8032 section 6. Verification only:
# it handles public data, so it does not need to be constant-time. Signing is never done
# here.

_P = 2 ** 255 - 19
_Q = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)


def _add(P, Q):
    a = (P[1] - P[0]) * (Q[1] - Q[0]) % _P
    b = (P[1] + P[0]) * (Q[1] + Q[0]) % _P
    c = 2 * P[3] * Q[3] * _D % _P
    d = 2 * P[2] * Q[2] % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(s, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _equal(P, Q):
    return ((P[0] * Q[2] - Q[0] * P[2]) % _P == 0
            and (P[1] * Q[2] - Q[1] * P[2]) % _P == 0)


def _recover_x(y, sign):
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P != 0:
        return None
    if (x & 1) != sign:
        x = _P - x
    return x


def _decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


_GY = 4 * pow(5, _P - 2, _P) % _P
_GX = _recover_x(_GY, 0)
_G = (_GX, _GY, 1, _GX * _GY % _P)


def verify_raw(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """RFC 8032 Ed25519 verification. True only for a valid signature."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    A = _decompress(public_key)
    R = _decompress(signature[:32])
    if A is None or R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public_key + message).digest(),
                       "little") % _Q
    return _equal(_mul(s, _G), _add(R, _mul(h, A)))


def verify_entry_signature(entry: dict, public_key: bytes) -> Tuple[bool, str]:
    """Check an entry's signature against a public key. Returns (ok, explanation).

    Does not recompute the content hash; callers check that separately, because a valid
    signature over a hash the content no longer matches proves nothing about the content.
    """
    trust = entry.get("trust") or {}
    sig_b64 = trust.get("signature_b64")
    kid = trust.get("signing_key_id")
    entry_hash = (entry.get("provenance") or {}).get("entry_hash_sha256") or ""
    if not sig_b64:
        return False, "entry is not signed"
    expected_kid = key_id(public_key)
    if kid != expected_kid:
        return False, f"signed by key {kid}, but the published key is {expected_kid}"
    try:
        sig = base64.b64decode(sig_b64, validate=True)
        msg = message_for(entry_hash)
    except Exception as ex:  # malformed base64 or hash
        return False, f"malformed signature or hash: {ex}"
    if verify_raw(public_key, msg, sig):
        return True, f"valid signature by {kid} over the content hash"
    return False, f"signature does not verify under {kid}"


# ── Signing (key holder only; needs the `cryptography` package) ───────────────

def private_key_path() -> Path:
    return Path(os.environ.get("QENCODE_SIGNING_KEY") or DEFAULT_PRIVATE_KEY_PATH)


def sign_entry_hash(entry_hash_hex: str, key_path: Optional[Path] = None) -> Tuple[str, str]:
    """Sign an entry hash with the Ed25519 private key at key_path. Returns
    (signature_b64, key_id). Raises if the key is missing, unreadable or not Ed25519."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key_path = Path(key_path or private_key_path())
    key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError(f"{key_path} is not an Ed25519 private key")
    raw_pub = key.public_key().public_bytes(serialization.Encoding.Raw,
                                            serialization.PublicFormat.Raw)
    sig = key.sign(message_for(entry_hash_hex))
    # Never hand back a signature this module's own verifier would reject.
    if not verify_raw(raw_pub, message_for(entry_hash_hex), sig):
        raise RuntimeError("signature failed self-verification; refusing to use it")
    return base64.b64encode(sig).decode("ascii"), key_id(raw_pub)
