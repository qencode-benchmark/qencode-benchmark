#!/usr/bin/env python3
"""
Phase 15: Assign trust level to each benchmark entry and write trust block into JSON.

Usage:
  python scripts/assign_trust_levels.py --db-dir releases/v2/db
  python scripts/assign_trust_levels.py --file path/to/entry.json
  python scripts/assign_trust_levels.py --db-dir releases/v2/db --suite benchmarks/standard/suite_v1.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from qencode.trust import LEVEL_CERTIFIED, LEVEL_EXPERIMENTAL, LEVEL_VALIDATED, determine_trust_level


def main() -> None:
    ap = argparse.ArgumentParser(description="Assign trust level to benchmark entries")
    ap.add_argument("--file", help="Single entry JSON")
    ap.add_argument("--db-dir", help="Directory of entry JSONs")
    ap.add_argument("--suite", default=None, help="Standard suite YAML for certified check (default: benchmarks/standard/suite_v1.yaml)")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--gap-threshold", type=float, default=0.01, help="Gap threshold for trusted (default: 0.01)")
    args = ap.parse_args()

    repo = Path(args.repo_root or _REPO).resolve()
    suite_spec = None
    if args.suite or True:
        try:
            from qencode.standard_suite import load_standard_suite
            suite_path = Path(args.suite or str(repo / "benchmarks" / "standard" / "suite_v1.yaml")).resolve()
            if suite_path.exists():
                suite_spec = load_standard_suite(suite_path)
        except Exception:
            pass

    paths: List[Path] = []
    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = (repo / p).resolve()
        if not p.exists():
            sys.exit(f"File not found: {p}")
        paths = [p]
    elif args.db_dir:
        db = Path(args.db_dir).resolve()
        if not db.is_dir():
            sys.exit(f"DB dir not found: {db}")
        ignore = {
            "index.json", "benchmarks.csv", "manifest.json", "entry_content_hashes.json",
            "trusted_index.json", "trusted_benchmarks.csv", "canonical_index.json",
        }
        paths = sorted(
            p for p in db.glob("*.json")
            if p.name not in ignore and "__sha256_" in p.name and "_v2__sha256_" in p.name
        )
    else:
        ap.error("Use --file or --db-dir")

    counts = {LEVEL_EXPERIMENTAL: 0, LEVEL_VALIDATED: 0, LEVEL_CERTIFIED: 0}
    for p in paths:
        try:
            entry = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"❌ {p.name}: read error {e}")
            continue
        level, reasons = determine_trust_level(entry, suite_spec=suite_spec, gap_threshold=args.gap_threshold)
        counts[level] = counts.get(level, 0) + 1
        entry = dict(entry)
        entry["trust"] = {
            "level": level,
            "reason": reasons,
            "suite_version": suite_spec.get("version") if suite_spec else None,
            "assigned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        p.write_text(json.dumps(entry, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  {p.name}: {level}")

    print()
    print(f"Assigned: {counts.get(LEVEL_EXPERIMENTAL, 0)} experimental, {counts.get(LEVEL_VALIDATED, 0)} validated, {counts.get(LEVEL_CERTIFIED, 0)} certified")


if __name__ == "__main__":
    main()
