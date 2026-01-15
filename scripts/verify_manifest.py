#!/usr/bin/env python3
from __future__ import annotations

"""
Verify a manifest.json produced by scripts/build_manifest.py.

Checks:
- each file exists
- file size matches
- sha256 matches
- overall_sha256 matches (based on the manifest's file list)

Usage:
  python3 scripts/verify_manifest.py --root releases/v2/trusted --manifest releases/v2/trusted/manifest.json
"""
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

Json = Dict[str, Any]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _overall_fingerprint(rows: List[Tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for rel, sha in sorted(rows, key=lambda t: t[0].lower()):
        h.update(f"{rel} {sha}\n".encode("utf-8"))
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--manifest", required=True)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve()

    m: Json = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = m.get("files")
    if not isinstance(files, list):
        raise SystemExit("manifest missing 'files' list")

    missing = 0
    bad_size = 0
    bad_sha = 0

    rows: List[Tuple[str, str]] = []

    for rec in files:
        if not isinstance(rec, dict):
            continue
        rel = rec.get("path")
        exp_bytes = rec.get("bytes")
        exp_sha = rec.get("sha256")
        if not isinstance(rel, str) or not isinstance(exp_bytes, int) or not isinstance(exp_sha, str):
            continue

        p = root / rel
        if not p.exists():
            missing += 1
            print(f"❌ missing: {rel}")
            continue

        got_bytes = p.stat().st_size
        if got_bytes != exp_bytes:
            bad_size += 1
            print(f"❌ size: {rel} expected={exp_bytes} got={got_bytes}")

        got_sha = _sha256_file(p)
        if got_sha != exp_sha:
            bad_sha += 1
            print(f"❌ sha256: {rel} expected={exp_sha} got={got_sha}")

        rows.append((rel, got_sha))

    got_overall = _overall_fingerprint(rows)
    exp_overall = m.get("overall_sha256")

    if not isinstance(exp_overall, str):
        raise SystemExit("manifest missing 'overall_sha256'")

    if got_overall != exp_overall:
        print(f"❌ overall_sha256 mismatch expected={exp_overall} got={got_overall}")
        raise SystemExit(2)

    if missing or bad_size or bad_sha:
        raise SystemExit(2)

    print(f"✅ verify_manifest: OK files={len(rows)} overall_sha256={got_overall}")


if __name__ == "__main__":
    main()

