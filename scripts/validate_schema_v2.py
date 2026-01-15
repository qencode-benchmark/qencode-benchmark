#!/usr/bin/env python3
"""
Validate v2 entries against a JSON schema.

Usage:
  python3 scripts/validate_schema_v2.py --db-dir releases/v2/db --schema schema/schema_v2.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import jsonschema

Json = Dict[str, Any]


def iter_entry_files(db_dir: Path) -> List[Path]:
    ignore = {"index.json", "benchmarks.csv"}
    return sorted([p for p in db_dir.rglob("*.json") if p.name not in ignore])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--schema", required=True)
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    schema_path = Path(args.schema)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")
    if not schema_path.exists():
        raise SystemExit(f"schema not found: {schema_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    ok = 0
    bad = 0
    for p in iter_entry_files(db_dir):
        data = json.loads(p.read_text(encoding="utf-8"))
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            bad += 1
            print(f"❌ {p.name}")
            for e in errors[:10]:
                loc = ".".join([str(x) for x in e.path]) or "<root>"
                print(f"   - {loc}: {e.message}")
        else:
            ok += 1
            print(f"✅ {p.name}")

    total = ok + bad
    print(f"\nDone. OK={ok}, BAD={bad}, Total={total}")
    if bad:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

