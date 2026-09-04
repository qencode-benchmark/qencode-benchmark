#!/usr/bin/env python3
# scripts/validate_schema_v2.py
from __future__ import annotations

"""
Validate v2 entry JSON files against schema v2.

Important: this validates ONLY entry JSON artifacts (not manifest/index/hashes).
Default selection rule: filenames containing "__sha256_" and ending in ".json".
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import jsonschema


def _iter_entry_files(db_dir: Path) -> List[Path]:
    # Entries follow: <name>__sha256_<hex>.json
    return sorted([p for p in db_dir.glob("*.json") if "__sha256_" in p.name])


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema(schema_path: Path) -> Dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--schema", required=True)
    args = ap.parse_args()

    db_dir = Path(args.db_dir).resolve()
    schema_path = Path(args.schema).resolve()

    if not db_dir.exists() or not db_dir.is_dir():
        raise SystemExit(f"--db-dir must be a directory: {db_dir}")
    if not schema_path.exists():
        raise SystemExit(f"--schema not found: {schema_path}")

    schema = _load_schema(schema_path)
    validator = jsonschema.Draft202012Validator(schema)

    ok = 0
    bad = 0

    files = _iter_entry_files(db_dir)
    if not files:
        raise SystemExit(f"No entry files found in {db_dir} (expected '*__sha256_*.json').")

    for path in files:
        try:
            data = _load_json(path)
            errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
            if errors:
                bad += 1
                print(f"❌ {path.name}")
                for e in errors[:50]:
                    where = ".".join(str(x) for x in e.path) if e.path else "<root>"
                    print(f"   - {where}: {e.message}")
            else:
                ok += 1
                print(f"✅ {path.name}")
        except Exception as exc:
            bad += 1
            print(f"❌ {path.name}\n   - exception: {exc}")

    print(f"\nDone. OK={ok}, BAD={bad}, Total={ok + bad}")
    if bad:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

