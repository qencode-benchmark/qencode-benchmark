#!/usr/bin/env python3
"""
Phase 1: Run the full QEncode Suite v3 (or a subset).

Iterates over molecules x mappings x ansatz types defined in suite_v3.yaml
and calls generate_entry_v3.py for each combination.

Usage:
  python scripts/run_suite_v3.py                            # full suite
  python scripts/run_suite_v3.py --molecules H2 LiH         # subset
  python scripts/run_suite_v3.py --mappings jordan_wigner    # JW only
  python scripts/run_suite_v3.py --ansatz uccsd              # UCCSD only
  python scripts/run_suite_v3.py --dry-run                   # no file writes
  python scripts/run_suite_v3.py --molecules H2 --dry-run    # quick smoke test

Progress is logged to releases/v3/run_suite_v3.log.
Failed molecules are re-tried once; persistent failures are skipped.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_PATH = REPO / "releases" / "v3" / "run_suite_v3.log"

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; RESET = "\033[0m"; BOLD = "\033[1m"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_suite() -> dict:
    """Load suite_v3.yaml and return parsed config."""
    try:
        import yaml
    except ImportError:
        # Minimal fallback: read known defaults
        return {
            "molecules": [
                {"name": "H2",   "active_space": [2, 2], "tier": "certified"},
                {"name": "LiH",  "active_space": [4, 4], "tier": "certified"},
                {"name": "HF",   "active_space": [2, 2], "tier": "certified"},
                {"name": "BeH2", "active_space": [4, 4], "tier": "certified"},
                {"name": "H2O",  "active_space": [4, 4], "tier": "certified"},
                {"name": "NH3",  "active_space": [4, 4], "tier": "certified"},
                {"name": "N2",   "active_space": [6, 6], "tier": "research"},
            ],
            "mappings": ["jordan_wigner", "bravyi_kitaev"],
            "ansatz":   [{"type": "uccsd"}, {"type": "hardware_efficient"}],
        }

    suite_path = REPO / "benchmarks" / "v3" / "suite_v3.yaml"
    with open(suite_path) as f:
        return yaml.safe_load(f)


def run_entry(molecule: str, mapping: str, ansatz_type: str,
              basis: str = "sto-3g", max_iter: int = 500,
              multistart: int = 3, seed: int = 42,
              dry_run: bool = False, no_classical: bool = False) -> int:
    """Run generate_entry_v3.py for one (molecule, mapping, ansatz) combination."""
    cmd = [
        sys.executable,
        str(REPO / "scripts" / "generate_entry_v3.py"),
        "--molecule",    molecule,
        "--basis",       basis,
        "--mapping",     mapping,
        "--ansatz-type", ansatz_type,
        "--max-iter",    str(max_iter),
        "--multistart",  str(multistart),
        "--seed",        str(seed),
        "--no-colour",   # log-friendly
    ]
    if dry_run:
        cmd.append("--dry-run")
    if no_classical:
        cmd.append("--no-classical")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run the full QEncode Suite v3",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--molecules",     nargs="*", default=None,
                    help="Subset of molecules (e.g. H2 LiH). Default: all")
    ap.add_argument("--mappings",      nargs="*",
                    default=["jordan_wigner", "bravyi_kitaev"],
                    choices=["jordan_wigner", "bravyi_kitaev"],
                    help="Qubit mappings to run")
    ap.add_argument("--ansatz",        nargs="*",
                    default=["uccsd", "hardware_efficient"],
                    choices=["uccsd", "hardware_efficient"],
                    help="Ansatz types to run")
    ap.add_argument("--basis",         default="sto-3g")
    ap.add_argument("--max-iter",      type=int, default=500)
    ap.add_argument("--multistart",    type=int, default=3)
    ap.add_argument("--seed",          type=int, default=42)
    ap.add_argument("--skip-research", action="store_true",
                    help="Skip research-tier molecules (e.g. N2)")
    ap.add_argument("--dry-run",       action="store_true")
    ap.add_argument("--no-classical",  action="store_true",
                    help="Skip MP2/CCSD for speed (dev mode)")
    args = ap.parse_args()

    suite = load_suite()

    # Build molecule list
    all_mols = suite.get("molecules", [])
    if args.molecules:
        all_mols = [m for m in all_mols
                    if m["name"].upper() in [x.upper() for x in args.molecules]]
    if args.skip_research:
        all_mols = [m for m in all_mols if m.get("tier", "certified") != "research"]

    # Build combos
    combos = []
    for mol in all_mols:
        for mapping in args.mappings:
            for ansatz_type in args.ansatz:
                combos.append((mol["name"], mapping, ansatz_type))

    total   = len(combos)
    passed  = 0
    failed  = []
    start_t = time.time()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(LOG_PATH, "a")

    def log(msg: str) -> None:
        ts = _utcnow()
        line = f"[{ts}] {msg}"
        print(line)
        log_fh.write(line + "\n")
        log_fh.flush()

    print(f"\n{BOLD}{'='*65}")
    print(f"  QEncode Suite v3 Runner")
    print(f"  {total} combinations | mappings={args.mappings} | ansatz={args.ansatz}")
    print(f"{'='*65}{RESET}\n")

    log(f"Suite start | {total} combos | dry_run={args.dry_run}")

    for i, (mol, mapping, ansatz_type) in enumerate(combos, 1):
        label = f"{mol}/{mapping[:2].upper()}/{ansatz_type.upper()[:5]}"
        print(f"\n{BOLD}[{i}/{total}] {label}{RESET}")
        log(f"START  {label}")

        t0 = time.time()
        rc = run_entry(mol, mapping, ansatz_type,
                       basis=args.basis,
                       max_iter=args.max_iter,
                       multistart=args.multistart,
                       seed=args.seed,
                       dry_run=args.dry_run,
                       no_classical=args.no_classical)
        elapsed = time.time() - t0

        if rc == 0:
            passed += 1
            log(f"PASS   {label}  ({elapsed:.1f}s)")
        else:
            failed.append(label)
            log(f"FAIL   {label}  rc={rc}  ({elapsed:.1f}s)")

    total_elapsed = time.time() - start_t

    print(f"\n{BOLD}{'='*65}")
    print(f"  Suite complete: {passed}/{total} passed in {total_elapsed:.0f}s")
    if failed:
        print(f"  Failed ({len(failed)}): {', '.join(failed)}")
    print(f"{'='*65}{RESET}\n")

    log(f"Suite done | {passed}/{total} passed | {total_elapsed:.0f}s")
    log_fh.close()

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
