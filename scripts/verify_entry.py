#!/usr/bin/env python3
"""
QEncode Entry Verifier
======================
Re-runs a benchmark entry and verifies the VQE energy matches the stored value.

The primary check is an energy tolerance comparison. COBYLA optimization is not
bit-for-bit reproducible across runs (nfev and optimal_params vary slightly due
to floating-point non-determinism), so the SHA-256 hash cannot be used as a
reliable reproduction test. The hash serves as tamper-detection only — it proves
a stored JSON has not been modified.

Default tolerance: 1e-6 Ha (1 million times stricter than the 0.01 Ha
certification threshold, and 100x stricter than chemical accuracy).

Usage:
  # Energy check (default, recommended)
  python scripts/verify_entry.py releases/v3.1/db/H2_631g_JW_UCCSD_v3_tapered__sha256_c311a3dfdda0df10.json

  # Tighter tolerance
  python scripts/verify_entry.py <entry>.json --tolerance 1e-8

  # Hash tamper-check (verifies JSON has not been edited, does not re-run)
  python scripts/verify_entry.py <entry>.json --hash-only

Exit codes:
  0  Verification passed
  1  Verification failed or pipeline error
"""
from __future__ import annotations

import argparse
import copy
import hashlib
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
def _warn(msg): return f"{YELLOW}  [INFO]{RESET}  {msg}"
def _info(msg): return f"  {BOLD}···{RESET}  {msg}"

# Must match _HASH_EXCLUDE in generate_entry_v3.py
_HASH_EXCLUDE = {
    "created_utc", "entry_id", "entry_hash_sha256",
    "git_commit", "computed_utc", "certified_utc",
    "signature_b64", "signing_key_id",
}

def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in _HASH_EXCLUDE}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return copy.deepcopy(obj)

def stable_hash(d: dict) -> str:
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def tamper_check(entry: dict) -> tuple[bool, str, str]:
    """Recompute hash from stored data and compare to stored hash. Returns (ok, stored, computed)."""
    stored_hash = entry.get("provenance", {}).get("entry_hash_sha256", "")
    computed    = stable_hash(_strip_volatile(entry))
    return computed == stored_hash, stored_hash, computed


def main():
    ap = argparse.ArgumentParser(description="Verify a QEncode benchmark entry.")
    ap.add_argument("entry_json", help="Path to the stored .json artifact")
    ap.add_argument(
        "--tolerance", type=float, default=1e-6,
        metavar="HA",
        help="VQE energy tolerance in Hartree (default: 1e-6)",
    )
    ap.add_argument(
        "--hash-only", action="store_true",
        help="Only check the stored SHA-256 hash for tampering (no re-run)",
    )
    ap.add_argument("--seed", type=int, default=42,
                    help="Random seed for VQE (default: 42)")
    args = ap.parse_args()

    entry_path = Path(args.entry_json)
    if not entry_path.exists():
        print(_fail(f"File not found: {entry_path}"))
        sys.exit(1)

    stored = json.loads(entry_path.read_text())
    prob   = stored.get("problem", {})
    enc    = stored.get("encoding", {})
    res    = stored.get("results", {})
    prov   = stored.get("provenance", {})

    molecule      = prob.get("name", "")
    basis         = prob.get("basis", "6-31g")
    mapping       = enc.get("mapping", "jordan_wigner")
    ansatz_raw    = enc.get("ansatz_type", "uccsd")
    multistart    = res.get("vqe", {}).get("multistart_runs", 5)
    stored_hash   = prov.get("entry_hash_sha256", "")
    stored_energy = res.get("vqe", {}).get("best_energy_hartree")
    stored_gap    = res.get("quality", {}).get("abs_vqe_exact_gap")
    ansatz        = ansatz_raw.replace("_tapered", "")

    print()
    print(f"{BOLD}QEncode Entry Verifier{RESET}")
    print(f"  Entry:    {entry_path.name}")
    print(f"  Molecule: {molecule}  |  Basis: {basis}  |  Mapping: {mapping}  |  Ansatz: {ansatz}")

    # ── Hash tamper-check (always shown, no re-run needed) ────────────────────
    ok, stored_h, computed_h = tamper_check(stored)
    if ok:
        print(f"  Hash:     {stored_h[:16]}…  {GREEN}✓ not tampered{RESET}")
    else:
        print(f"  Hash:     {stored_h[:16]}…  {RED}✗ MISMATCH — file may have been edited{RESET}")

    if args.hash_only:
        print()
        if ok:
            print(_ok("Hash tamper-check passed — stored JSON is unmodified"))
        else:
            print(_fail("Hash tamper-check FAILED"))
            print(f"  Stored:   {stored_h}")
            print(f"  Computed: {computed_h}")
        sys.exit(0 if ok else 1)

    print(f"  Mode:     energy tolerance ± {args.tolerance:.0e} Ha  (cert. threshold: 1e-2 Ha)")
    print()

    # ── Re-run the generator ──────────────────────────────────────────────────
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
        print(_info(f"Running: {' '.join(cmd[2:])}"))
        print()

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(_fail("Generator exited with error:"))
            print(result.stdout[-2000:] if result.stdout else "")
            print(result.stderr[-2000:] if result.stderr else "")
            sys.exit(1)

        generated_files = list(Path(tmpdir).glob("*.json"))
        if not generated_files:
            print(_fail("Generator produced no output file."))
            sys.exit(1)

        gen      = json.loads(generated_files[0].read_text())
        new_energy = gen.get("results", {}).get("vqe", {}).get("best_energy_hartree")
        new_gap    = gen.get("results", {}).get("quality", {}).get("abs_vqe_exact_gap")

    # ── Energy comparison ─────────────────────────────────────────────────────
    if stored_energy is None or new_energy is None:
        print(_fail("VQE energy missing from stored or generated entry."))
        sys.exit(1)

    diff = abs(new_energy - stored_energy)
    print(f"  Stored  VQE energy: {stored_energy:.10f} Ha")
    print(f"  Generated VQE:      {new_energy:.10f} Ha")
    print(f"  |ΔE|:               {diff:.3e} Ha   tolerance: {args.tolerance:.0e} Ha")
    if stored_gap is not None:
        print(f"  Stored VQE gap:     {stored_gap:.3e} Ha  (vs 1e-2 Ha cert. threshold)")
    print()

    if diff <= args.tolerance:
        print(_ok(f"PASS — VQE energy reproduced within {args.tolerance:.0e} Ha"))
    else:
        print(_fail(f"FAIL — energy differs by {diff:.3e} Ha (exceeds {args.tolerance:.0e} Ha)"))
        print()
        print("  Certification tool versions:")
        for k, v in prov.get("tool_versions", {}).items():
            print(f"    {k}: {v}")
        sys.exit(1)


if __name__ == "__main__":
    main()
