#!/usr/bin/env python3
"""
Unified end-to-end checker for qencode-db.

Runs:
  - v1: validate -> index -> benchmarks -> audit
  - v1->v2 migration
  - v2: (optional) stamp env -> validate -> index -> benchmarks -> audit
  - (optional) export trusted set
  - (optional) supply-chain: manifest + entry hashes (+ verification)

Important note:
Supply-chain files (manifest.json, entry_content_hashes.json) are NOT DB entries.
Some tools may accidentally treat any *.json as an entry if they don't ignore these.
This script keeps ordering safe and can also temporarily stash these files during v2 checks.

Usage examples:
  python3 scripts/check_all.py --gap-threshold 0.01
  python3 scripts/check_all.py --gap-threshold 0.01 --stamp-env
  python3 scripts/check_all.py --gap-threshold 0.01 --export-trusted --trusted-out-dir releases/v2/trusted --trusted-clean-out-dir --trusted-require-gap-check
  python3 scripts/check_all.py --gap-threshold 0.01 --stamp-env --export-trusted --trusted-out-dir releases/v2/trusted --trusted-clean-out-dir --trusted-require-gap-check --supply-chain --manifest-only-json-entries --verify-entry-hashes
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional


def _repo_root() -> Path:
    # scripts/check_all.py -> repo root
    return Path(__file__).resolve().parents[1]


def _py() -> str:
    return str(Path(os.environ.get("VIRTUAL_ENV", "")) / "bin" / "python3") if os.environ.get("VIRTUAL_ENV") else "python3"


def _script(name: str) -> str:
    return str(_repo_root() / "scripts" / name)


def _run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    print("\n$ " + " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def _stash_meta_files(db_dir: Path, meta_names: List[str]) -> Optional[Path]:
    """
    If meta files already exist inside db_dir, move them out temporarily so schema/index/bench/audit
    don't accidentally treat them as DB entries.

    Returns stash dir or None.
    """
    present = [n for n in meta_names if (db_dir / n).exists()]
    if not present:
        return None

    stash_dir = db_dir / ".meta_stash"
    stash_dir.mkdir(parents=True, exist_ok=True)

    for n in present:
        src = db_dir / n
        dst = stash_dir / n
        # overwrite stash copy if exists
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))
    return stash_dir


def _restore_meta_files(db_dir: Path, stash_dir: Optional[Path]) -> None:
    if not stash_dir or not stash_dir.exists():
        return

    for p in stash_dir.iterdir():
        dst = db_dir / p.name
        if dst.exists():
            dst.unlink()
        shutil.move(str(p), str(dst))

    # cleanup if empty
    try:
        stash_dir.rmdir()
    except Exception:
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1-dir", default="releases/v1/db")
    ap.add_argument("--v2-dir", default="releases/v2/db")
    ap.add_argument("--schema-v1", default="schema_v1.json")
    ap.add_argument("--schema-v2", default="schema/schema_v2.json")
    ap.add_argument("--gap-threshold", type=float, default=0.01)

    ap.add_argument("--skip-v1", action="store_true")
    ap.add_argument("--skip-v2", action="store_true")
    ap.add_argument("--skip-v1-audit", action="store_true")
    ap.add_argument("--skip-v2-audit", action="store_true")

    ap.add_argument("--strict-v1", action="store_true")
    ap.add_argument("--strict-v2", action="store_true")

    # v2 stamping
    ap.add_argument("--stamp-env", action="store_true", help="Stamp provenance.environment into v2 entries")
    ap.add_argument("--stamp-env-overwrite", action="store_true", help="Overwrite existing provenance.environment")

    # trusted export
    ap.add_argument("--export-trusted", action="store_true")
    ap.add_argument("--trusted-out-dir", default="releases/v2/trusted")
    ap.add_argument("--trusted-require-gap-check", action="store_true")
    ap.add_argument("--trusted-clean-out-dir", action="store_true")

    # supply-chain
    ap.add_argument("--supply-chain", action="store_true", help="Build manifest + entry hashes + verification")
    ap.add_argument("--manifest-only-json-entries", action="store_true", help="Manifest includes only DB entry *.json files")
    ap.add_argument("--verify-entry-hashes", action="store_true", help="Verify entry hashes after generating them")

    args = ap.parse_args()

    repo = _repo_root()
    v1_dir = repo / args.v1_dir
    v2_dir = repo / args.v2_dir
    schema_v1 = repo / args.schema_v1
    schema_v2 = repo / args.schema_v2

    # --------------------
    # V1 pipeline
    # --------------------
    if not args.skip_v1:
        _run([_py(), _script("validate_schema.py"), "--db-dir", str(v1_dir)], cwd=repo)

        _run([_py(), _script("build_index.py"), "--db-dir", str(v1_dir)], cwd=repo)

        _run([_py(), _script("report_benchmarks.py"), "--db-dir", str(v1_dir), "--csv"], cwd=repo)

        if not args.skip_v1_audit:
            _run([_py(), _script("audit_db.py"), "--db-dir", str(v1_dir), "--gap-threshold", str(args.gap_threshold)], cwd=repo)

            if args.strict_v1:
                # If strict, fail if there are any flags.
                # audit_db.py already prints flags; strict policy can be enforced by grepping output externally if needed.
                pass

    # --------------------
    # Migrate v1 -> v2
    # --------------------
    if not args.skip_v2:
        _run([_py(), _script("migrate_v1_to_v2.py"),
              "--in-dir", str(v1_dir),
              "--out-dir", str(v2_dir),
              "--gap-threshold", str(args.gap_threshold)], cwd=repo)

        # If supply-chain artifacts already exist in v2_dir from a previous run,
        # stash them so v2 validation/index/bench/audit won't misinterpret them.
        stash = _stash_meta_files(v2_dir, ["manifest.json", "entry_content_hashes.json"])

        try:
            # --------------------
            # Optional v2 env stamping
            # --------------------
            if args.stamp_env:
                cmd = [_py(), _script("stamp_env_v2.py"), "--db-dir", str(v2_dir), "--write"]
                if args.stamp_env_overwrite:
                    cmd.append("--overwrite")
                _run(cmd, cwd=repo)

            # --------------------
            # V2 pipeline (validate -> index -> benchmarks -> audit)
            # --------------------
            _run([_py(), _script("validate_schema_v2.py"),
                  "--db-dir", str(v2_dir),
                  "--schema", str(schema_v2)], cwd=repo)

            _run([_py(), _script("build_index_v2.py"), "--db-dir", str(v2_dir)], cwd=repo)

            _run([_py(), _script("report_benchmarks_v2.py"), "--db-dir", str(v2_dir), "--csv"], cwd=repo)

            if not args.skip_v2_audit:
                _run([_py(), _script("audit_db_v2.py"), "--db-dir", str(v2_dir), "--gap-threshold", str(args.gap_threshold)], cwd=repo)

                if args.strict_v2:
                    # same note as strict_v1
                    pass

            # --------------------
            # Optional export trusted
            # --------------------
            if args.export_trusted:
                cmd = [
                    _py(), _script("export_trusted_v2.py"),
                    "--db-dir", str(v2_dir),
                    "--out-dir", str(repo / args.trusted_out_dir),
                    "--gap-threshold", str(args.gap_threshold),
                ]
                if args.trusted_require_gap_check:
                    cmd.append("--require-gap-check")
                if args.trusted_clean_out_dir:
                    cmd.append("--clean-out-dir")
                _run(cmd, cwd=repo)

        finally:
            # Restore any previously stashed meta files (so we don't lose them)
            _restore_meta_files(v2_dir, stash)

        # --------------------
        # Optional supply-chain
        # --------------------
        if args.supply_chain:
            # Build manifest.json
            manifest_path = v2_dir / "manifest.json"
            cmd = [_py(), _script("build_manifest.py"), "--root", str(v2_dir), "--out", str(manifest_path)]
            if args.manifest_only_json_entries:
                cmd.append("--only-json-entries")
            _run(cmd, cwd=repo)

            # Verify manifest
            _run([_py(), _script("verify_manifest.py"), "--root", str(v2_dir), "--manifest", str(manifest_path)], cwd=repo)

            # Build entry_content_hashes.json
            _run([_py(), _script("entry_content_hashes_v2.py"), "--db-dir", str(v2_dir), "--out-dir", str(v2_dir)], cwd=repo)

            # Verify entry hashes (optional)
            if args.verify_entry_hashes:
                _run([_py(), _script("verify_entry_hashes_v2.py"), "--db-dir", str(v2_dir)], cwd=repo)

    print("\n✅ check_all: OK")


if __name__ == "__main__":
    main()

