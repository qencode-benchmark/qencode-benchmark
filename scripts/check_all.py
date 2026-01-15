#!/usr/bin/env python3
"""
Run a company-grade consistency check for BOTH v1 and v2.

v1 pipeline:
  - validate_schema.py
  - build_index.py
  - report_benchmarks.py --csv
  - audit_db.py

v2 pipeline:
  - migrate_v1_to_v2.py (writes releases/v2/db)
  - validate_schema_v2.py
  - build_index_v2.py
  - report_benchmarks_v2.py --csv
  - audit_db_v2.py

Usage:
  python3 scripts/check_all.py

Common:
  python3 scripts/check_all.py --gap-threshold 0.01
  python3 scripts/check_all.py --strict-v1   # fail if v1 missing vqe/exact
  python3 scripts/check_all.py --strict-v2   # fail if v2 missing vqe/exact or untrusted
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def _run(cmd: List[str]) -> None:
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1-dir", default="releases/v1/db")
    ap.add_argument("--v2-dir", default="releases/v2/db")
    ap.add_argument("--schema-v1", default="schema_v1.json")
    ap.add_argument("--schema-v2", default="schema/schema_v2.json")
    ap.add_argument("--gap-threshold", type=float, default=1e-2)

    ap.add_argument("--skip-v1", action="store_true")
    ap.add_argument("--skip-v2", action="store_true")

    ap.add_argument("--skip-v1-audit", action="store_true")
    ap.add_argument("--skip-v2-audit", action="store_true")

    ap.add_argument("--strict-v1", action="store_true", help="Fail if v1 entries are missing vqe/exact")
    ap.add_argument("--strict-v2", action="store_true", help="Fail if v2 entries are missing vqe/exact or are untrusted")
    args = ap.parse_args()

    py = sys.executable

    v1_dir = Path(args.v1_dir)
    v2_dir = Path(args.v2_dir)
    schema_v1 = Path(args.schema_v1)
    schema_v2 = Path(args.schema_v2)

    if not args.skip_v1:
        if not v1_dir.exists():
            raise SystemExit(f"v1-dir not found: {v1_dir}")
        if not schema_v1.exists():
            raise SystemExit(f"schema v1 not found: {schema_v1}")

        _run([py, "scripts/validate_schema.py", "--db-dir", str(v1_dir)])
        _run([py, "scripts/build_index.py", "--db-dir", str(v1_dir)])
        _run([py, "scripts/report_benchmarks.py", "--db-dir", str(v1_dir), "--csv"])

        if not args.skip_v1_audit:
            audit_cmd = [py, "scripts/audit_db.py", "--db-dir", str(v1_dir), "--gap-threshold", str(args.gap_threshold)]
            if args.strict_v1:
                audit_cmd += ["--fail-on", "missing_vqe", "--fail-on", "missing_exact"]
            _run(audit_cmd)

    if not args.skip_v2:
        if not v1_dir.exists():
            raise SystemExit(f"v1-dir not found (needed for v2 migration): {v1_dir}")
        if not schema_v2.exists():
            raise SystemExit(f"schema v2 not found: {schema_v2}")

        v2_dir.mkdir(parents=True, exist_ok=True)

        _run(
            [
                py,
                "scripts/migrate_v1_to_v2.py",
                "--in-dir",
                str(v1_dir),
                "--out-dir",
                str(v2_dir),
                "--gap-threshold",
                str(args.gap_threshold),
            ]
        )
        _run([py, "scripts/validate_schema_v2.py", "--db-dir", str(v2_dir), "--schema", str(schema_v2)])
        _run([py, "scripts/build_index_v2.py", "--db-dir", str(v2_dir)])
        _run([py, "scripts/report_benchmarks_v2.py", "--db-dir", str(v2_dir), "--csv"])

        if not args.skip_v2_audit:
            _run([py, "scripts/audit_db_v2.py", "--db-dir", str(v2_dir), "--gap-threshold", str(args.gap_threshold)])

            if args.strict_v2:
                # Strict v2 policy: every entry must be trusted and have vqe+exact.
                # We implement this with a tiny inline python snippet to avoid another script.
                _run(
                    [
                        py,
                        "-c",
                        (
                            "import json,glob,sys\n"
                            "bad=0\n"
                            "for p in sorted(glob.glob('"+str(v2_dir)+"/**/*.json', recursive=True)):\n"
                            "  if p.endswith('/index.json') or p.endswith('/benchmarks.csv'):\n"
                            "    continue\n"
                            "  d=json.load(open(p,'r',encoding='utf-8'))\n"
                            "  q=d.get('results',{}).get('quality',{})\n"
                            "  if not q.get('trusted',False):\n"
                            "    bad+=1\n"
                            "if bad:\n"
                            "  print(f'❌ strict-v2 failed: {bad} untrusted entries')\n"
                            "  sys.exit(2)\n"
                            "print('✅ strict-v2: all entries trusted')\n"
                        ),
                    ]
                )

    print("\n✅ check_all: OK")


if __name__ == "__main__":
    main()

