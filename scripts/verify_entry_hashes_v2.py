#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict


HASH_FILE = "entry_content_hashes.json"


def _canonical_json_bytes(obj: Any) -> bytes:
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    args = ap.parse_args()

    db_dir = Path(args.db_dir).resolve()
    if not db_dir.is_dir():
        raise SystemExit(f"--db-dir must be a directory: {db_dir}")

    hash_path = db_dir / HASH_FILE
    if not hash_path.exists():
        raise SystemExit(f"Missing {HASH_FILE} in {db_dir}. Run entry_content_hashes_v2.py first.")

    payload = json.loads(hash_path.read_text(encoding="utf-8"))
    if payload.get("format") != "qencode-db.entry_content_hashes.v2":
        raise SystemExit("entry_content_hashes.json has unexpected format.")

    hashes: Dict[str, str] = payload.get("hashes", {})
    if not isinstance(hashes, dict) or not hashes:
        raise SystemExit("entry_content_hashes.json has no hashes.")

    bad = 0
    checked = 0

    for fname, expected in sorted(hashes.items()):
        fpath = db_dir / fname
        if not fpath.exists():
            bad += 1
            print(f"❌ missing file: {fname}")
            continue

        data = json.loads(fpath.read_text(encoding="utf-8"))
        got = _sha256_hex(_canonical_json_bytes(data))
        checked += 1

        if got != expected:
            bad += 1
            print(f"❌ hash mismatch: {fname}")
            print(f"   expected={expected}")
            print(f"   got     ={got}")

    if bad:
        raise SystemExit(2)

    print(f"✅ verify_entry_hashes_v2: OK checked={checked} files")


if __name__ == "__main__":
    main()

