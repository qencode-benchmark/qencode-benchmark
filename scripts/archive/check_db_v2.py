#!/usr/bin/env python3
"""
One-command v2 pipeline:
- migrate v1 -> v2
- validate v2 schema

Usage:
  python3 scripts/check_db_v2.py --in-dir releases/v1/db --out-dir releases/v2/db --schema schema/schema_v2.json
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def run(cmd: List[str]) -> None:
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--schema", required=True)
    ap.add_argument("--gap-threshold", type=float, default=1e-2)
    ap.add_argument("--skip-migrate", action="store_true")
    args = ap.parse_args()

    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    schema = Path(args.schema)
    if not in_dir.exists():
        raise SystemExit(f"in-dir not found: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    if not schema.exists():
        raise SystemExit(f"schema not found: {schema}")

    py = sys.executable

    if not args.skip_migrate:
        run(
            [
                py,
                "scripts/migrate_v1_to_v2.py",
                "--in-dir",
                str(in_dir),
                "--out-dir",
                str(out_dir),
                "--gap-threshold",
                str(args.gap_threshold),
            ]
        )

    run([py, "scripts/validate_schema_v2.py", "--db-dir", str(out_dir), "--schema", str(schema)])
    print("\n✅ check_db_v2: OK")


if __name__ == "__main__":
    main()
