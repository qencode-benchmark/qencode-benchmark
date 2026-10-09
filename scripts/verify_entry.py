#!/usr/bin/env python3
"""
QEncode Entry Verifier
======================
Checks a stored entry, then re-runs it and compares the result with what was published.

Checks that need no re-run come first, and each one fails the verification:

  content hash   the SHA-256 recomputed from the stored JSON must equal the stored hash.
                 This detects an edit made without recomputing the hash. It is a
                 checksum, not a signature: anyone can edit an entry and recompute it,
                 so it does not show who produced the entry.
  consistency    the stored gap must equal |E_VQE - E_exact| from the stored energies,
                 and the stored tier (certified / research) must follow from that gap.

Then the generator is re-run with the entry's recorded settings and seed:

  strict         (default) the regenerated energy must match the stored one to
                 --tolerance (default 1e-6 Ha). This is the determinism guarantee and it
                 holds on the reference pinned environment.
  certification  the regenerated entry must reach the SAME outcome as the published one:
                 a certified entry must still certify, a research-tier entry must still
                 not. Energy movement is reported but not gated on. Use this across
                 machines, where gradient-free trajectories are not bit-identical.

Usage:
  python scripts/verify_entry.py releases/v4/db/<entry>.json
  python scripts/verify_entry.py <entry>.json --mode certification
  python scripts/verify_entry.py <entry>.json --hash-only     # no re-run, seconds

Supports schema 3.x and 4.x entries (releases/v3*, releases/v4).

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

# Must match _HASH_EXCLUDE in the pipeline; test_verifier_and_pipeline_agree_on_which
# _fields_are_volatile enforces it. "machine" is provenance.environment.machine: recorded
# so an entry says where it ran, excluded from the hash so that the same numbers hash the
# same on any machine.
_HASH_EXCLUDE = {
    "created_utc", "entry_id", "entry_hash_sha256",
    "git_commit", "computed_utc", "certified_utc",
    "signature_b64", "signing_key_id", "machine",
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


# The pipeline writes the gap as abs(E_VQE - E_exact) from the same two stored floats, so
# a faithful entry recomputes it exactly; the tolerance only absorbs JSON round-tripping.
_GAP_RECOMPUTE_TOL_HA = 1e-12


def consistency_check(entry: dict) -> tuple[bool, list[str]]:
    """Do the stored numbers agree with each other? Returns (ok, report lines).

    v4 entries measure the gap against the exact ground state of the tapered qubit
    Hamiltonian; v3 entries, which do not store that energy, against CASCI.
    """
    res = entry.get("results") or {}
    q   = res.get("quality") or {}
    ref = res.get("reference") or {}
    e_vqe = (res.get("vqe") or {}).get("best_energy_hartree")
    gap   = q.get("abs_vqe_exact_gap")
    trusted = q.get("trusted")
    if ref.get("exact_qubit_ground_energy_hartree") is not None:
        e_ref, ref_name = ref["exact_qubit_ground_energy_hartree"], "exact qubit ground state"
    else:
        e_ref, ref_name = ref.get("casci_ground_energy_hartree"), "CASCI"

    missing = [n for n, v in (("VQE energy", e_vqe), ("reference energy", e_ref),
                              ("gap", gap), ("trusted flag", trusted)) if v is None]
    if missing:
        return False, [f"stored entry is missing: {', '.join(missing)}"]

    lines, ok = [], True
    recomputed = abs(e_vqe - e_ref)
    if abs(recomputed - gap) <= _GAP_RECOMPUTE_TOL_HA:
        lines.append(f"gap {gap:.3e} Ha = |E_VQE - E_ref| against the {ref_name}")
    else:
        ok = False
        lines.append(f"stored gap {gap:.6e} Ha but |E_VQE - E_ref| = {recomputed:.6e} Ha "
                     f"against the {ref_name}")
    if trusted == (gap < CERT_THRESHOLD_HA):
        lines.append(f"tier {'certified' if trusted else 'research'} follows from the gap "
                     f"(threshold {CERT_THRESHOLD_HA:.0e} Ha)")
    else:
        ok = False
        lines.append(f"stored tier says trusted={trusted}, but a gap of {gap:.3e} Ha is "
                     f"{'below' if gap < CERT_THRESHOLD_HA else 'not below'} the "
                     f"{CERT_THRESHOLD_HA:.0e} Ha threshold")
    level = (entry.get("trust") or {}).get("level")
    if level is not None and (level == "certified") != bool(trusted):
        ok = False
        lines.append(f"trust.level is '{level}' but results.quality.trusted is {trusted}")
    return ok, lines


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
        help="Only run the checks that need no re-run: the content hash and the "
             "consistency of the stored numbers. Takes seconds.",
    )
    ap.add_argument(
        "--ignore-hash", action="store_true",
        help="Report a content-hash mismatch but continue. For diagnosing an entry you "
             "edited on purpose; a verification run this way has not checked the hash.",
    )
    ap.add_argument("--seed", type=int, default=None,
                    help="Random seed for the re-run (default: the seed the entry "
                         "records in run_config.seed, else 42)")
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

    # The content-hash recipe and the generator flags below are those of schema 3.x and
    # 4.x. Older entries (releases/v1, v2) were hashed differently and cannot be re-run
    # by the current generators, so the verifier says so instead of failing obscurely.
    schema_ver = str(stored.get("schema_version", ""))
    if not schema_ver.startswith(("3.", "4.")):
        print(_fail(f"Schema version '{schema_ver}' is not supported; this verifier "
                    f"handles schema 3.x and 4.x entries."))
        sys.exit(1)

    # ── Checks that need no re-run. Each one fails the verification. ──────────
    hash_ok, stored_h, computed_h = tamper_check(stored)
    if hash_ok:
        print(f"  Hash:     {stored_h[:16]}…  {GREEN}✓ matches the stored content{RESET}")
    else:
        print(f"  Hash:     {stored_h[:16]}…  {RED}✗ MISMATCH — the file was edited "
              f"after it was hashed{RESET}")
        print(f"            stored   {stored_h}")
        print(f"            computed {computed_h}")

    cons_ok, cons_lines = consistency_check(stored)
    mark = f"{GREEN}✓{RESET}" if cons_ok else f"{RED}✗{RESET}"
    for i, line in enumerate(cons_lines):
        print(f"  {'Numbers:' if i == 0 else '         '} {mark} {line}")

    trust = stored.get("trust") or {}
    if trust.get("signature_b64"):
        print(f"  Signed:   present (key {trust.get('signing_key_id')}), NOT checked by "
              f"this verifier")
    else:
        print(f"  Signed:   no — this entry carries no signature")

    if not hash_ok and not args.ignore_hash:
        print()
        print(_fail("Content hash does not match: the stored entry was modified after it "
                    "was hashed. Not re-running. (--ignore-hash to continue anyway.)"))
        sys.exit(1)
    if not cons_ok:
        print()
        print(_fail("The stored numbers are inconsistent with each other; see above."))
        sys.exit(1)

    if args.hash_only:
        print()
        if not hash_ok:
            print(_fail("Content hash does not match the stored entry"))
            sys.exit(1)
        print(_ok("Stored entry is internally consistent and matches its hash"))
        return

    stored_trusted = bool((stored.get("results") or {}).get("quality", {}).get("trusted"))
    seed = args.seed
    if seed is None:
        seed = (stored.get("run_config") or {}).get("seed")
    if seed is None:
        seed = 42

    if args.mode == "certification":
        print(f"  Mode:     certification — the regenerated entry must reach the published "
              f"outcome ({'certified' if stored_trusted else 'research tier'})")
    else:
        print(f"  Mode:     strict — energy must match to ± {args.tolerance:.0e} Ha "
              f"(reference pinned environment only)")
    print()

    # ── Re-run the generator ──────────────────────────────────────────────────
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
            "--seed",        str(seed),
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
    # reaches the outcome it was published with. This mode asks that instead, and reports
    # the energy movement without gating on it.
    #
    # "The published outcome" covers both tiers. The first version asked only "does it
    # certify?", so a research-tier entry -- published precisely because it does not --
    # failed every run: N2 JW/UCCSD (10.83 mHa) was the one failure in the weekly job of
    # 2026-09-06, and it was correct behaviour by the entry, not a regression.
    if args.mode == "certification":
        if new_gap is None:
            print(_fail("Regenerated entry has no gap; cannot check certification."))
            sys.exit(1)
        new_trusted = new_gap < CERT_THRESHOLD_HA
        published = "certified" if stored_trusted else "research tier"
        regenerated = "certifies" if new_trusted else "does not certify"
        print(f"  Mode:     certification — published as {published}; "
              f"the regenerated entry {regenerated}.")
        print(f"            energy movement is reported, not gated on.")
        print()
        if new_trusted == stored_trusted:
            print(_ok(f"PASS — published outcome reproduced: regenerated gap "
                      f"{new_gap:.3e} Ha, threshold {CERT_THRESHOLD_HA:.0e} Ha "
                      f"(energy moved {diff:.3e} Ha)"))
        elif stored_trusted:
            print(_fail(f"FAIL — published as certified, but the regenerated gap "
                        f"{new_gap:.3e} Ha exceeds the {CERT_THRESHOLD_HA:.0e} Ha "
                        f"threshold (energy moved {diff:.3e} Ha)"))
            sys.exit(1)
        else:
            print(_fail(f"FAIL — published as research tier, but the regenerated gap "
                        f"{new_gap:.3e} Ha is below the {CERT_THRESHOLD_HA:.0e} Ha "
                        f"threshold (energy moved {diff:.3e} Ha): the published tier "
                        f"does not hold on this machine"))
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
