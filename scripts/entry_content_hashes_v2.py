#!/usr/bin/env python3
from __future__ import annotations

"""
Compute deterministic content hashes for v2 JSON entries without modifying them.

We hash a canonical JSON serialization (sorted keys, compact separators) after removing
volatile fields that should not affect "scientific identity".

Removals (best-effort):
- provenance.environment.generated_utc
- provenance.created_utc / generated_utc (if present)

Outputs:
- entry_content_hashes.json (mapping)
- entry_content_hashes.csv (table)

Usage:
  python3 scripts/entry_content_hashes_v2.py --db-dir releases/v2/db --out-dir releases/v2/db
  python3 scripts/entry_content_hashes_v2.py --db-dir releases/v2/trusted --out-dir releases/v2/trusted
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Json = Dict[str, Any]


IGNORE_FILENAMES = {
    "index.json",
    "trusted_index.json",
    "manifest.json",
}


def _iter_entry_files(db_dir: Path) -> List[Path]:
    files = [p for p in db_dir.rglob("*.json") if p.is_file() and p.name not in IGNORE_FILENAMES]
    return sorted(files, key=lambda p: p.as_posix().lower())


def _del_nested(d: Json, path: List[str]) -> None:
    cur: Any = d
    for k in path[:-1]:
        if not isinstance(cur, dict) or k not in cur:
            return
        cur = cur[k]
    if isinstance(cur, dict):
        cur.pop(path[-1], None)


def _canonical_bytes(d: Json) -> bytes:
    s = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return s.encode("utf-8")


def _content_hash(d: Json) -> str:
    h = hashlib.sha256()
    h.update(_canonical_bytes(d))
    return h.hexdigest()


def _entry_id(d: Json, fallback: str) -> str:
    v = d.get("entry_id") or d.get("id")
    return v if isinstance(v, str) and v else fallback


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    db_dir = Path(args.db_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_json = out_dir / "entry_content_hashes.json"
    out_csv = out_dir / "entry_content_hashes.csv"

    rows: List[Tuple[str, str, str]] = []  # (file, entry_id, sha256)
    mapping: Dict[str, Any] = {"entries": []}

    for p in _iter_entry_files(db_dir):
        d: Json = json.loads(p.read_text(encoding="utf-8"))

        # Remove volatile timestamps only (keep environment fingerprint itself)
        _del_nested(d, ["provenance", "environment", "generated_utc"])
        _del_nested(d, ["provenance", "created_utc"])
        _del_nested(d, ["provenance", "generated_utc"])

        eid = _entry_id(d, fallback=p.stem)
        sha = _content_hash(d)

        rel = p.relative_to(db_dir).as_posix()
        rows.append((rel, eid, sha))
        mapping["entries"].append({"file": rel, "entry_id": eid, "entry_content_sha256": sha})

    out_json.write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "entry_id", "entry_content_sha256"])
        for rel, eid, sha in rows:
            w.writerow([rel, eid, sha])

    print(f"✅ entry_content_hashes_v2: OK entries={len(rows)} out={out_dir}")


if __name__ == "__main__":
    main()

