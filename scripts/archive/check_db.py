#!/usr/bin/env python3
"""
One-command "company-safety" check for the DB.

Runs, in order:
1) schema validation
2) build index.json
3) build benchmarks.csv (report)
4) audit_db.py

Usage:
  python3 scripts/check_db.py --db-dir releases/v1/db --schema schema_v1.json

Common variants:
  python3 scripts/check_db.py --db-dir releases/v1/db --schema schema_v1.json --skip-audit
  python3 scripts/check_db.py --db-dir releases/v1/db --schema schema_v1.json --audit-fail-on missing_exact --audit-fail-on vqe_gap
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
    ap.add_argument("--db-dir", required=True, help="DB directory like releases/v1/db")
    ap.add_argument("--schema", required=True, help="Schema path like schema_v1.json")

    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument("--skip-index", action="store_true")
    ap.add_argument("--skip-benchmarks", action="store_true")
    ap.add_argument("--skip-audit", action="store_true")

    ap.add_argument("--audit-gap-threshold", type=float, default=1e-2)
    ap.add_argument("--audit-fail-on", action="append", default=[], help="Pass through to audit_db.py --fail-on")
    ap.add_argument("--audit-out-csv", default=None)

    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    schema = Path(args.schema)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")
    if not schema.exists():
        raise SystemExit(f"schema not found: {schema}")

    py = sys.executable

    if not args.skip_validate:
        _run([py, "scripts/validate_schema.py", "--db-dir", str(db_dir)])

    if not args.skip_index:
        _run([py, "scripts/build_index.py", "--db-dir", str(db_dir)])

    if not args.skip_benchmarks:
        _run([py, "scripts/report_benchmarks.py", "--db-dir", str(db_dir), "--csv"])

    if not args.skip_audit:
        cmd = [py, "scripts/audit_db.py", "--db-dir", str(db_dir), "--gap-threshold", str(args.audit_gap_threshold)]
        for x in args.audit_fail_on or []:
            cmd.extend(["--fail-on", x])
        if args.audit_out_csv:
            cmd.extend(["--out-csv", args.audit_out_csv])
        _run(cmd)

    print("\n✅ check_db: OK")


if __name__ == "__main__":
    main()
