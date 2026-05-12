#!/usr/bin/env python3
"""
QEncode Entry Verifier
======================
Re-runs a benchmark entry from a stored JSON artifact and checks that the
SHA-256 provenance hash matches.  Proves the result is independently
reproducible with the same tool versions.

Usage:
  python scripts/verify_entry.py releases/v3.1/db/H2_631g_JW_UCCSD_v3_tapered__sha256_c311a3dfdda0df10.json
  python scripts/verify_entry.py releases/v3.1/db/HF_631g_JW_UCCSD_v3_tapered__sha256_027087b777a912eb.json
  python scripts/verify_entry.py releases/v3.1/db/H2_631g_JW_UCCSD_v3_tapered__sha256_c311a3dfdda0df10.json --tolerance 1e-6

Flags:
  --tolerance FLOAT   Accept if |new_VQE - stored_VQE| < tolerance instead of
                      checking the exact SHA-256 hash.  Useful when library
                      versions differ slightly from those used at certification.

Exit codes:
  0  Verification passed
  1  Verification failed or pipeline error
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _ok(msg):   return f"{GREEN}  [PASS]{RESET}  {msg}"
def _fail(msg): return f"{RED}  [FAIL]{RESET}  {msg}"
def _info(msg): return f"  {BOLD}···{RESET}  {msg}"


def main():
    ap = argparse.ArgumentParser(description="Re-run a QEncode entry and verify its SHA-256 hash.")
    ap.add_argument("entry_json", help="Path to the stored .json artifact")
    ap.add_argument(
        "--tolerance", type=float, default=None,
        metavar="HA",
        help="Use energy tolerance check instead of exact hash (e.g. 1e-6)",
    )
    ap.add_argument("--seed", type=int, default=42,
                    help="Random seed for VQE (default: 42)")
    args = ap.parse_args()

    entry_path = Path(args.entry_json)
    if not entry_path.exists():
        print(_fail(f"File not found: {entry_path}"))
        sys.exit(1)

    # ── Load stored entry ──────────────────────────────────────────────────────
    stored = json.loads(entry_path.read_text())
    prob   = stored.get("problem", {})
    enc    = stored.get("encoding", {})
    res    = stored.get("results", {})
    prov   = stored.get("provenance", {})

    molecule     = prob.get("name", "")
    basis        = prob.get("basis", "6-31g")
    mapping      = enc.get("mapping", "jordan_wigner")
    ansatz_raw   = enc.get("ansatz_type", "uccsd")
    multistart   = res.get("vqe", {}).get("multistart_runs", 5)
    stored_hash  = prov.get("entry_hash_sha256", "")
    stored_energy = res.get("vqe", {}).get("best_energy_hartree")

    # Strip _tapered suffix — the generator adds it automatically
    ansatz = ansatz_raw.replace("_tapered", "")

    print()
    print(f"{BOLD}QEncode Entry Verifier{RESET}")
    print(f"  Entry:      {entry_path.name}")
    print(f"  Molecule:   {molecule}  |  Basis: {basis}  |  Mapping: {mapping}  |  Ansatz: {ansatz}")
    print(f"  Multistart: {multistart}  |  Seed: {args.seed}")
    if args.tolerance is not None:
        print(f"  Mode:       energy tolerance ± {args.tolerance:.2e} Ha")
    else:
        print(f"  Mode:       exact SHA-256 hash")
    print(f"  Stored hash (16): {stored_hash[:16]}…")
    print()

    # ── Re-run generate_entry_v3.py into a temp dir ────────────────────────────
    generator = REPO / "scripts" / "generate_entry_v3.py"
    if not generator.exists():
        print(_fail(f"Generator not found: {generator}"))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            sys.executable, str(generator),
            "--molecule",    molecule,
            "--basis",       basis,
            "--mapping",     mapping,
            "--ansatz-type", ansatz,
            "--multistart",  str(multistart),
            "--seed",        str(args.seed),
            "--out-dir",     tmpdir,
            "--no-colour",
        ]

        print(_info(f"Running: {' '.join(cmd[2:])}"))  # skip python path for brevity
        print()

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(_fail("Generator exited with error:"))
            print(result.stdout[-2000:] if result.stdout else "")
            print(result.stderr[-2000:] if result.stderr else "")
            sys.exit(1)

        # Find the generated file
        generated_files = list(Path(tmpdir).glob("*.json"))
        if not generated_files:
            print(_fail("Generator produced no output file."))
            print(result.stdout[-2000:])
            sys.exit(1)

        generated = json.loads(generated_files[0].read_text())
        new_hash   = generated.get("provenance", {}).get("entry_hash_sha256", "")
        new_energy = generated.get("results", {}).get("vqe", {}).get("best_energy_hartree")
        new_gap    = generated.get("results", {}).get("quality", {}).get("abs_vqe_exact_gap")

    # ── Compare ────────────────────────────────────────────────────────────────
    print(f"  Stored  hash:   {stored_hash}")
    print(f"  Generated hash: {new_hash}")
    print()

    if args.tolerance is not None:
        if stored_energy is None or new_energy is None:
            print(_fail("Cannot compare energies — VQE energy missing from one entry."))
            sys.exit(1)
        diff = abs(new_energy - stored_energy)
        print(f"  Stored  VQE energy: {stored_energy:.10f} Ha")
        print(f"  Generated VQE:      {new_energy:.10f} Ha")
        print(f"  |ΔE|:               {diff:.3e} Ha  (tolerance: {args.tolerance:.3e} Ha)")
        print()
        if diff <= args.tolerance:
            print(_ok(f"PASS — energy matches within {args.tolerance:.2e} Ha"))
            print(f"  VQE gap: {new_gap:.6e} Ha")
            sys.exit(0)
        else:
            print(_fail(f"FAIL — energy differs by {diff:.3e} Ha (exceeds {args.tolerance:.2e} Ha)"))
            sys.exit(1)
    else:
        if new_hash == stored_hash:
            print(_ok(f"PASS — SHA-256 hash matches exactly"))
            print(f"  {stored_hash}")
            sys.exit(0)
        else:
            print(_fail("FAIL — SHA-256 hash mismatch"))
            print(f"  Expected: {stored_hash}")
            print(f"  Got:      {new_hash}")
            print()
            print("  Tip: use --tolerance 1e-6 if library versions differ from those at certification.")
            print("  Certification tool versions:")
            for k, v in stored.get("provenance", {}).get("tool_versions", {}).items():
                print(f"    {k}: {v}")
            sys.exit(1)


if __name__ == "__main__":
    main()
