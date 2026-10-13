#!/usr/bin/env python3
"""Create the project signing key, and sign published entries with it.

Run by the key holder only. Needs the `cryptography` package, which the pinned v4
environment does not include on purpose; use a separate small environment:

    python -m venv ~/.qencode/signer-venv
    ~/.qencode/signer-venv/bin/pip install cryptography==50.0.1

Then, once:

    ~/.qencode/signer-venv/bin/python scripts/sign_entries.py keygen

writes the private key to ~/.qencode/qencode_ed25519_private.pem (mode 0600, never inside
the repository; QENCODE_SIGNING_KEY overrides the path) and the public key to
keys/qencode_ed25519_public.pem, which is committed.
BACK UP THE PRIVATE KEY. If it is lost, entries can no longer be signed under this key;
if it leaks, anyone can sign as QEncode and the key must be replaced and every entry
re-signed.

And whenever entries need signatures:

    ~/.qencode/signer-venv/bin/python scripts/sign_entries.py sign

For each entry in releases/v4/db it first runs the verifier's no-rerun checks (content
hash and consistency of the stored numbers) and refuses to sign an entry that fails them:
a signature over a hash the content does not match would certify nothing. It then signs,
verifies the signature with the standard-library verifier, and writes back only
trust.signature_b64 and trust.signing_key_id, in the pipeline's own JSON format. Already
validly signed entries are left alone.

The private key is read by this process and never printed. The script prints only the
public key id.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = REPO / "releases" / "v4" / "db"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("qencode_signing", REPO / "src" / "qencode" / "signing.py")
VE = _load("verify_entry", REPO / "scripts" / "verify_entry.py")


def _write_entry(path: Path, entry: dict) -> None:
    # The pipeline writes json.dumps(entry, indent=2, ensure_ascii=True) with no trailing
    # newline (generate_entry_v4.py); matching it keeps the diff to the two signed fields.
    path.write_text(json.dumps(entry, indent=2, ensure_ascii=True))


def keygen(args) -> int:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv_path = S.private_key_path()
    pub_path = S.PUBLIC_KEY_PATH
    if priv_path.exists():
        print(f"refusing: a private key already exists at {priv_path}", file=sys.stderr)
        return 1
    if pub_path.exists():
        print(f"refusing: a public key is already published at {pub_path}; replacing it "
              f"would orphan every existing signature", file=sys.stderr)
        return 1

    key = Ed25519PrivateKey.generate()
    priv_path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(priv_path.parent, 0o700)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    fd = os.open(priv_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(pem)

    pub_pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)
    pub_path.parent.mkdir(parents=True, exist_ok=True)
    pub_path.write_bytes(pub_pem)
    raw = S.public_key_from_pem(pub_pem)
    print(f"private key: {priv_path}  (mode 600 -- back it up now, somewhere offline)")
    print(f"public key:  {pub_path.relative_to(REPO)}  (commit this)")
    print(f"key id:      {S.key_id(raw)}")
    return 0


def sign(args) -> int:
    from cryptography.hazmat.primitives import serialization

    priv_path = S.private_key_path()
    if not priv_path.exists():
        print(f"no private key at {priv_path}; run `keygen` first", file=sys.stderr)
        return 1
    published = S.load_public_key()
    if published is None:
        print(f"no published public key at {S.PUBLIC_KEY_PATH}", file=sys.stderr)
        return 1
    key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    own = key.public_key().public_bytes(serialization.Encoding.Raw,
                                        serialization.PublicFormat.Raw)
    if own != published:
        print(f"refusing: the private key at {priv_path} does not belong to the published "
              f"public key {S.key_id(published)}", file=sys.stderr)
        return 1

    files = sorted(Path(args.db).glob("*.json"))
    signed = skipped = 0
    refused = []
    for path in files:
        entry = json.loads(path.read_text())
        hash_ok = VE.tamper_check(entry)[0]
        cons_ok, why = VE.consistency_check(entry)
        if not (hash_ok and cons_ok):
            refused.append((path.name, "hash mismatch" if not hash_ok else "; ".join(why)))
            continue
        if S.verify_entry_signature(entry, published)[0]:
            skipped += 1
            continue

        h = entry["provenance"]["entry_hash_sha256"]
        sig_b64, kid = S.sign_entry_hash(h, priv_path)
        new = copy.deepcopy(entry)
        new["trust"]["signature_b64"] = sig_b64
        new["trust"]["signing_key_id"] = kid

        # Signing must not change anything the hash covers, nor any other field.
        before, after = copy.deepcopy(entry), copy.deepcopy(new)
        for d in (before, after):
            d["trust"].pop("signature_b64"), d["trust"].pop("signing_key_id")
        assert before == after, path.name
        assert VE.tamper_check(new)[0], path.name
        ok, why = S.verify_entry_signature(new, published)
        assert ok, f"{path.name}: {why}"

        if not args.dry_run:
            _write_entry(path, new)
        signed += 1

    verb = "would sign" if args.dry_run else "signed"
    print(f"{len(files)} entries: {verb} {signed}, already signed {skipped}, "
          f"refused {len(refused)}  (key {S.key_id(published)})")
    for name, why in refused:
        print(f"  refused {name}: {why}")
    return 1 if refused else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("keygen", help="create the project key pair (once)")
    sp = sub.add_parser("sign", help="sign every entry in a release directory")
    sp.add_argument("--db", default=str(DB), help="directory of entries (default: releases/v4/db)")
    sp.add_argument("--dry-run", action="store_true", help="check and sign in memory, write nothing")
    args = ap.parse_args()
    return keygen(args) if args.cmd == "keygen" else sign(args)


if __name__ == "__main__":
    sys.exit(main())
