# scripts/check_all.py
#!/usr/bin/env python3
"""
Run a company-grade consistency check for BOTH v1 and v2, with optional trusted export and v2 env stamping.

v1 pipeline:
  - validate_schema.py
  - build_index.py
  - report_benchmarks.py --csv
  - audit_db.py

v2 pipeline:
  - migrate_v1_to_v2.py
  - (optional) stamp_env_v2.py
  - validate_schema_v2.py
  - build_index_v2.py
  - report_benchmarks_v2.py --csv
  - audit_db_v2.py
  - (optional) export_trusted_v2.py
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

    ap.add_argument("--strict-v1", action="store_true")
    ap.add_argument("--strict-v2", action="store_true")

    # v2 env stamping
    ap.add_argument("--stamp-env", action="store_true", help="Stamp provenance.environment into v2 entries")
    ap.add_argument("--stamp-env-overwrite", action="store_true", help="Overwrite provenance.environment if present")

    # Trusted export (v2)
    ap.add_argument("--export-trusted", action="store_true", help="Export trusted v2 set after v2 checks")
    ap.add_argument("--trusted-out-dir", default="releases/v2/trusted", help="Where to write trusted export")
    ap.add_argument(
        "--trusted-require-gap-check",
        action="store_true",
        help="Only export entries with both VQE+exact and abs_gap <= threshold",
    )
    ap.add_argument(
        "--trusted-clean-out-dir",
        action="store_true",
        help="Delete trusted out dir contents before writing",
    )

    args = ap.parse_args()

    py = sys.executable

    v1_dir = Path(args.v1_dir)
    v2_dir = Path(args.v2_dir)
    schema_v1 = Path(args.schema_v1)
    schema_v2 = Path(args.schema_v2)
    trusted_out_dir = Path(args.trusted_out_dir)

    if not args.skip_v1:
        if not v1_dir.exists():
            raise SystemExit(f"v1-dir not found: {v1_dir}")
        if not schema_v1.exists():
            raise SystemExit(f"schema v1 not found: {schema_v1}")

        _run([py, "scripts/validate_schema.py", "--db-dir", str(v1_dir)])
        _run([py, "scripts/build_index.py", "--db-dir", str(v1_dir)])
        _run([py, "scripts/report_benchmarks.py", "--db-dir", str(v1_dir), "--csv"])

        if not args.skip_v1_audit:
            _run([py, "scripts/audit_db.py", "--db-dir", str(v1_dir), "--gap-threshold", str(args.gap_threshold)])
            if args.strict_v1:
                print("⚠️  strict-v1 requested, but v1 audit is non-fatal by design. (OK)")

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

        if args.stamp_env:
            cmd = [py, "scripts/stamp_env_v2.py", "--db-dir", str(v2_dir), "--write"]
            if args.stamp_env_overwrite:
                cmd.append("--overwrite")
            _run(cmd)

        _run([py, "scripts/validate_schema_v2.py", "--db-dir", str(v2_dir), "--schema", str(schema_v2)])
        _run([py, "scripts/build_index_v2.py", "--db-dir", str(v2_dir)])
        _run([py, "scripts/report_benchmarks_v2.py", "--db-dir", str(v2_dir), "--csv"])

        if not args.skip_v2_audit:
            _run([py, "scripts/audit_db_v2.py", "--db-dir", str(v2_dir), "--gap-threshold", str(args.gap_threshold)])

            if args.strict_v2:
                _run(
                    [
                        py,
                        "-c",
                        (
                            "import json,glob,sys\n"
                            f"paths=sorted(glob.glob('{v2_dir}/**/*.json', recursive=True))\n"
                            "bad=0\n"
                            "for p in paths:\n"
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

        if args.export_trusted:
            export_cmd = [
                py,
                "scripts/export_trusted_v2.py",
                "--db-dir",
                str(v2_dir),
                "--out-dir",
                str(trusted_out_dir),
                "--gap-threshold",
                str(args.gap_threshold),
            ]
            if args.trusted_require_gap_check:
                export_cmd.append("--require-gap-check")
            if args.trusted_clean_out_dir:
                export_cmd.append("--clean-out-dir")
            _run(export_cmd)

    print("\n✅ check_all: OK")


if __name__ == "__main__":
    main()

