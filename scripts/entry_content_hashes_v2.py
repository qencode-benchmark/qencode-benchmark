#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


OUT_FILENAME = "entry_content_hashes.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_entry_file(p: Path) -> bool:
    # v2 entry artifacts follow: <name>__sha256_<hex>.json
    return p.suffix == ".json" and "__sha256_" in p.name


def _canonical_json_bytes(obj: Any) -> bytes:
    # Stable JSON bytes regardless of whitespace / formatting in file.
    s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    db_dir = Path(args.db_dir).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not db_dir.is_dir():
        raise SystemExit(f"--db-dir must be a directory: {db_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: List[Path] = sorted([p for p in db_dir.glob("*.json") if _is_entry_file(p)])
    if not entries:
        raise SystemExit(f"No entry files found in {db_dir} (expected '*__sha256_*.json').")

    mapping: Dict[str, str] = {}
    for p in entries:
        data = json.loads(p.read_text(encoding="utf-8"))
        mapping[p.name] = _sha256_hex(_canonical_json_bytes(data))

    out_path = out_dir / OUT_FILENAME
    payload = {
        "format": "qencode-db.entry_content_hashes.v2",
        "generated_utc": _utc_now(),
        "count": len(mapping),
        "hashes": mapping,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ entry_content_hashes_v2: OK entries={len(mapping)} out={out_path}")


if __name__ == "__main__":
    main()

