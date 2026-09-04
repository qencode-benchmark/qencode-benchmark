#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

def safe_get(d: Dict[str, Any], path: list, default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur

def safe_set(d: Dict[str, Any], path: list, value):
    cur = d
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value

def migrate_one(data: Dict[str, Any]) -> bool:
    """
    Returns True if changed.
    """
    changed = False

    # Ensure vqe_run exists
    if "validation" not in data or not isinstance(data["validation"], dict):
        data["validation"] = {}
        changed = True
    if "vqe_run" not in data["validation"] or not isinstance(data["validation"]["vqe_run"], dict):
        data["validation"]["vqe_run"] = {}
        changed = True

    vqe_run = data["validation"]["vqe_run"]

    # If canonical field already exists, do nothing
    if vqe_run.get("best_energy_hartree_like") is not None:
        return changed

    # Try to find legacy values in common places
    legacy_candidates = [
        (["validation", "vqe_simple_search", "best_energy"], "vqe_simple_search"),
        (["validation", "vqe", "best_energy"], "vqe"),
        (["validation", "vqe_run", "estimated_ground_energy"], "estimated_ground_energy"),
    ]

    found_val = None
    found_src = None
    for path, src in legacy_candidates:
        val = safe_get(data, path, None)
        if val is not None:
            try:
                found_val = float(val)
                found_src = src
                break
            except Exception:
                pass

    if found_val is None:
        return changed

    # Write canonical field
    vqe_run["best_energy_hartree_like"] = found_val
    vqe_run.setdefault("optimizer", None)
    vqe_run.setdefault("method", "legacy_import")
    vqe_run["imported_from"] = found_src
    vqe_run["imported_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    changed = True

    return changed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="DB directory containing JSON entries")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change but do not write")
    args = ap.parse_args()

    db_dir = Path(args.db_dir).expanduser().resolve()
    files = sorted([p for p in db_dir.glob("*.json") if p.name != "index.json"])

    changed_count = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        changed = migrate_one(data)
        if changed:
            changed_count += 1
            print(f"🛠️  canonicalized: {f.name}")
            if not args.dry_run:
                f.write_text(json.dumps(data, indent=2), encoding="utf-8")

    print(f"\nDone. changed={changed_count} / total={len(files)}")

if __name__ == "__main__":
    main()

