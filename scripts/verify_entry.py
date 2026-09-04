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

# The published certification threshold. An entry is certified when its gap to the
# active-space CASCI reference is below this.
CERT_THRESHOLD_HA = 1e-2


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
    # The generator refuses to write an entry when the tree is dirty or the installed
    # packages differ from the pins. That is right when producing an entry, and it also
    # made the verifier unusable for anyone whose environment is not byte-identical to
    # ours -- which is everyone verifying our work from outside. These pass the override
    # through so a verification can proceed, loudly, on a drifted machine.
    ap.add_argument(
        "--mode", choices=("strict", "certification"), default="strict",
        help="strict: the regenerated energy must match the published one to "
             "--tolerance. This is the determinism guarantee and it holds on the "
             "reference pinned environment. certification: the regenerated entry must "
             "still meet the certification threshold; energy movement is reported but "
             "not gated on. Use this across machines, where gradient-free trajectories "
             "are not expected to be bit-identical (default: strict)")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="verify even if the git tree has uncommitted changes")
    ap.add_argument("--allow-env-drift", action="store_true",
                    help="verify even if installed package versions differ from the pins")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the generator command this entry would be re-run with, "
                         "then exit without running it. The reconstruction of that "
                         "command from the stored entry is where two of the three "
                         "verifier bugs lived (ansatz vocabulary, iteration budget), and "
                         "it is deterministic on any machine, unlike the energy.")
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
    # Entries record the ansatz in the pipeline's internal vocabulary, which is not the
    # same as its command line vocabulary: 29 of the 54 published entries store "hea",
    # and --ansatz-type rejects that. Without this mapping the verifier -- the tool that
    # backs the claim that any published result can be independently rebuilt -- cannot
    # re-run those entries at all.
    _ANSATZ_CLI = {"hea": "hardware_efficient",
                   "hardware_efficient": "hardware_efficient",
                   "uccsd": "uccsd",
                   "adapt": "adapt"}
    ansatz        = ansatz_raw.replace("_tapered", "")
    ansatz        = _ANSATZ_CLI.get(ansatz, ansatz)

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

    if args.mode == "certification":
        print(f"  Mode:     certification — regenerated gap must stay below "
              f"{CERT_THRESHOLD_HA:.0e} Ha")
    else:
        print(f"  Mode:     strict — energy must match to ± {args.tolerance:.0e} Ha "
              f"(reference pinned environment only)")
    print()

    # ── Re-run the generator ──────────────────────────────────────────────────
    schema_ver = stored.get("schema_version", "3.0.0")
    if schema_ver.startswith("4."):
        generator = REPO / "scripts" / "generate_entry_v4.py"
    else:
        generator = REPO / "scripts" / "generate_entry_v3.py"
    if not generator.exists():
        print(_fail(f"Generator not found: {generator}"))
        sys.exit(1)

    print(_info(f"Schema version: {schema_ver} → using {generator.name}"))

    # Build base command; add v4-only flags when applicable
    orbital_opt = prob.get("orbital_optimization", "hf") if schema_ver.startswith("4.") else None

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
        if args.allow_dirty:
            cmd.append("--allow-dirty")
        if args.allow_env_drift:
            cmd.append("--allow-env-drift")

        # The optimiser iteration cap must come from the entry, not from the generator's
        # default. A full sweep of all 54 published entries separated perfectly on this:
        # every entry recorded at the 500 default reproduced, and every entry recorded
        # above it failed, because the verifier silently re-ran them at 500 and they
        # landed somewhere else.
        max_iter = (stored.get("run_config") or {}).get("max_iterations")
        if max_iter:
            cmd += ["--max-iter", str(int(max_iter))]

        if orbital_opt and orbital_opt != "hf":
            cmd += ["--orbital-opt", orbital_opt]

        # v4.3: reproduce with the SAME ansatz depth, optimizer, and ADAPT config
        # that produced the stored entry — otherwise HEA/ADAPT entries re-run with
        # default settings and fail to reproduce.
        enc_v = stored.get("encoding", {})
        rc_v  = stored.get("run_config", {})
        reps_v = enc_v.get("ansatz_reps")
        if ansatz in ("hardware_efficient", "hea") and reps_v:
            cmd += ["--reps", str(reps_v)]

        opt_raw = str(rc_v.get("optimizer", "")).lower()
        if ansatz != "adapt":
            if "bfgs" in opt_raw:
                cmd += ["--optimizer", "bfgs"]
            elif "adam" in opt_raw:
                cmd += ["--optimizer", "adam"]
                import re as _re
                m = _re.search(r"lr=([0-9.eE+-]+)", opt_raw)
                if m:
                    cmd += ["--learning-rate", m.group(1)]
            # else: cobyla (default)

        if ansatz == "adapt":
            am = enc_v.get("adapt_metadata") or {}
            if am.get("gradient_threshold") is not None:
                cmd += ["--adapt-threshold", str(am["gradient_threshold"])]
            if am.get("max_operators") is not None:
                cmd += ["--adapt-max-ops", str(am["max_operators"])]
        print(_info(f"Running: {' '.join(cmd[2:])}"))
        print()

        if args.dry_run:
            print(_ok("Dry run: command reconstructed, generator not executed."))
            return

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
    print(f"  |ΔE|:               {diff:.3e} Ha")
    if stored_gap is not None:
        print(f"  Stored VQE gap:     {stored_gap:.3e} Ha")
    if new_gap is not None:
        print(f"  Regenerated gap:    {new_gap:.3e} Ha  (cert. threshold "
              f"{CERT_THRESHOLD_HA:.0e} Ha)")
    print()

    # ── Certification mode ────────────────────────────────────────────────────
    #
    # A gradient-free optimiser chooses its next step by comparing two nearly equal
    # energies, so a last-bit arithmetic difference can flip a comparison and send the run
    # into a different local minimum. Two simulator backends agreeing to 1e-13 Ha have
    # landed 11 mHa apart after COBYLA (docs/DEFERRED_TRACKS_FEASIBILITY.md). A different
    # machine is a larger perturbation than that.
    #
    # So bit-level energy agreement is a property of the reference pinned environment, not
    # of the method. Across machines the meaningful question is whether the entry still
    # satisfies the criterion it was certified under. This mode asks that instead, and
    # reports the energy movement without gating on it.
    if args.mode == "certification":
        if new_gap is None:
            print(_fail("Regenerated entry has no gap; cannot check certification."))
            sys.exit(1)
        print(f"  Mode:     certification — does the regenerated entry still certify?")
        print(f"            energy movement is reported, not gated on.")
        print()
        if new_gap < CERT_THRESHOLD_HA:
            print(_ok(f"PASS — regenerated gap {new_gap:.3e} Ha is within the "
                      f"{CERT_THRESHOLD_HA:.0e} Ha certification threshold "
                      f"(energy moved {diff:.3e} Ha)"))
        else:
            print(_fail(f"FAIL — regenerated gap {new_gap:.3e} Ha exceeds the "
                        f"{CERT_THRESHOLD_HA:.0e} Ha certification threshold"))
            sys.exit(1)
        return

    if diff <= args.tolerance:
        print(_ok(f"PASS — VQE energy reproduced within {args.tolerance:.0e} Ha"))
    else:
        print(_fail(f"FAIL — energy differs by {diff:.3e} Ha (exceeds {args.tolerance:.0e} Ha)"))
        print()
        print("  This is a strict determinism check and it only holds on the reference")
        print("  pinned environment. Across machines, use --mode certification; see")
        print("  docs/VERIFICATION_SWEEP.md.")
        print()
        print("  Certification tool versions:")
        for k, v in prov.get("tool_versions", {}).items():
            print(f"    {k}: {v}")
        sys.exit(1)


if __name__ == "__main__":
    main()
