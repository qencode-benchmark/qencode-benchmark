"""Entry signatures: the verifier is checked against the standard, then against the data.

src/qencode/signing.py verifies Ed25519 with the standard library so that anyone can check
a signature with nothing installed. A hand-written verifier is only worth trusting if it
agrees with the specification, so the first tests are the RFC 8032 section 7.1 test
vectors, plus the ways a signature should fail. Where the `cryptography` package is
installed, a signature it produces must verify here as well.

The last test is the claim the documentation makes: every published v4 entry carries a
valid signature by the published key, over a hash its content still matches.

    pytest tests/test_signing.py -v
"""
from __future__ import annotations

import base64
import copy
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("qencode_signing", REPO / "src" / "qencode" / "signing.py")
VE = _load("verify_entry", REPO / "scripts" / "verify_entry.py")

# RFC 8032 section 7.1, TEST 1-3 and TEST SHA(abc): (public key, message, signature)
RFC8032 = [
    ("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
     "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
     "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
     "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]


@pytest.mark.parametrize("pub,msg,sig", RFC8032, ids=["test1", "test2", "test3"])
def test_rfc8032_vectors_verify(pub, msg, sig):
    assert S.verify_raw(bytes.fromhex(pub), bytes.fromhex(msg), bytes.fromhex(sig))


@pytest.mark.parametrize("pub,msg,sig", RFC8032, ids=["test1", "test2", "test3"])
def test_rfc8032_vectors_reject_a_changed_message(pub, msg, sig):
    assert not S.verify_raw(bytes.fromhex(pub), bytes.fromhex(msg) + b"\x00", bytes.fromhex(sig))


def test_a_flipped_signature_bit_is_rejected():
    pub, msg, sig = (bytes.fromhex(x) for x in RFC8032[1])
    for i in (0, 31, 32, 63):
        bad = bytearray(sig)
        bad[i] ^= 1
        assert not S.verify_raw(pub, msg, bytes(bad)), i


def test_a_non_canonical_s_is_rejected():
    """s >= group order would let a signature be re-encoded into a second valid one."""
    pub, msg, sig = (bytes.fromhex(x) for x in RFC8032[1])
    s = int.from_bytes(sig[32:], "little") + S._Q
    assert not S.verify_raw(pub, msg, sig[:32] + s.to_bytes(32, "little"))


def test_wrong_lengths_are_rejected_not_raised():
    pub, msg, sig = (bytes.fromhex(x) for x in RFC8032[0])
    assert not S.verify_raw(pub[:31], msg, sig)
    assert not S.verify_raw(pub, msg, sig[:63])


def test_pem_round_trip_and_key_id():
    raw = bytes.fromhex(RFC8032[0][0])
    pem = (b"-----BEGIN PUBLIC KEY-----\n"
           + base64.b64encode(S._SPKI_ED25519_PREFIX + raw) + b"\n"
           + b"-----END PUBLIC KEY-----\n")
    assert S.public_key_from_pem(pem) == raw
    assert S.key_id(raw).startswith("ed25519:") and len(S.key_id(raw)) == len("ed25519:") + 16


def test_the_message_binds_the_hash_and_a_prefix():
    h = "a" * 64
    assert S.message_for(h) == b"qencode/entry-sha256/v1:" + h.encode()
    with pytest.raises(ValueError):
        S.message_for("A" * 64)
    with pytest.raises(ValueError):
        S.message_for("a" * 63)


def test_signatures_from_the_cryptography_package_verify_here(tmp_path):
    crypto = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    from cryptography.hazmat.primitives import serialization
    key = crypto.Ed25519PrivateKey.generate()
    path = tmp_path / "k.pem"
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                       serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))
    raw_pub = key.public_key().public_bytes(serialization.Encoding.Raw,
                                            serialization.PublicFormat.Raw)
    for i in range(20):
        h = f"{i:064x}"
        sig_b64, kid = S.sign_entry_hash(h, path)
        assert kid == S.key_id(raw_pub)
        assert S.verify_raw(raw_pub, S.message_for(h), base64.b64decode(sig_b64))
        assert not S.verify_raw(raw_pub, S.message_for(f"{i + 1:064x}"), base64.b64decode(sig_b64))


# ── The published claim ───────────────────────────────────────────────────────

def _published_key():
    key = S.load_public_key()
    assert key is not None, f"no published public key at {S.PUBLIC_KEY_PATH.relative_to(REPO)}"
    return key


def test_every_published_v4_entry_is_signed_by_the_published_key():
    key = _published_key()
    bad = []
    for p in sorted((REPO / "releases" / "v4" / "db").glob("*.json")):
        d = json.loads(p.read_text())
        hash_ok = VE.tamper_check(d)[0]
        sig_ok, why = S.verify_entry_signature(d, key)
        if not (hash_ok and sig_ok):
            bad.append((p.name, hash_ok, why))
    assert not bad, bad


def test_a_signed_entry_with_edited_content_no_longer_verifies_end_to_end():
    """Edit a number and recompute the hash: the checksum passes, the signature cannot."""
    key = _published_key()
    p = REPO / "releases" / "v4" / "db" / "H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_93a0f8a8604d9aed.json"
    d = copy.deepcopy(json.loads(p.read_text()))
    d["run_config"]["max_iterations"] = 1
    d["provenance"]["entry_hash_sha256"] = VE.stable_hash(VE._strip_volatile(d))
    assert VE.tamper_check(d)[0]
    assert not S.verify_entry_signature(d, key)[0]
