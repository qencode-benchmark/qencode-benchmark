#!/usr/bin/env python3
"""
estimate_ft_resources.py — fault-tolerant resource estimates for QEncode entries.

A VQE gap says how accurately an algorithm reconstructs a reference energy. It says
nothing about what it would cost to obtain that energy on a fault-tolerant machine.
This computes the second number, for the same Hamiltonians, from data already stored
in every published entry — no new quantum or classical simulation is performed.

WHAT THIS IS
------------
An estimate of the cost of qubitized quantum phase estimation (QPE) applied to each
entry's qubit Hamiltonian, under one explicitly stated cost model. It is a model
evaluation, not a measurement, and not a compiled circuit. Different papers make
different constant-factor choices; ours are written down below so a reader can
recompute or disagree with them rather than having to trust the output.

THE MODEL
---------
Write the qubit Hamiltonian as a linear combination of unitaries (LCU),

    H = sum_a  h_a P_a ,   L = number of Pauli terms,   lambda = sum_a |h_a| .

Qubitization [1] builds a walk operator whose spectrum encodes E/lambda, so the cost
of QPE is set by lambda rather than by the spectral norm of H. Estimating E to
additive precision eps requires

    N_walk = ceil( pi * lambda / (2 * eps) )                                    (1)

applications of the walk operator. Each walk step is one PREPARE, one SELECT and a
reflection. Using alias sampling for PREPARE and unary iteration for SELECT [1,2],
each costs O(L) Toffolis, so at leading order

    toffolis_per_walk = 2 * L + mu                                              (2)

with mu the number of bits used to hold the coefficients (the arithmetic and
reflection costs are subleading and are absorbed here). Total Toffolis are
N_walk * toffolis_per_walk, and we convert with

    1 Toffoli = 4 T gates                                                       (3)

which is the measurement-assisted construction; a synthesis-only account would use 7.

Logical qubits are counted as the system register plus the ancillae the construction
needs:

    logical = n_system + ceil(log2 L)      index register
                       + ceil(log2 L)      unary-iteration ancillae
                       + mu                coefficient / keep register
                       + 1                 phase ancilla (iterative QPE)          (4)

WHAT THIS DELIBERATELY DOES NOT DO
----------------------------------
No physical-qubit or wall-clock estimate. That needs a code distance, a physical error
rate and a cycle time, and the result is dominated by those assumptions rather than by
the chemistry. Quoting a physical qubit count here would look more informative than it
is. The logical counts above are the honest stopping point.

No claim that QPE and VQE are being compared like for like. VQE here targets a CASCI
reference inside an active space; these numbers say what QPE would cost on that same
active-space Hamiltonian to a stated precision. They are complementary, not rival,
figures.

REFERENCES
----------
[1] R. Babbush, C. Gidney, D. W. Berry, N. Wiebe, J. McClean, A. Paler, A. Fowler and
    H. Neven, "Encoding Electronic Spectra in Quantum Circuits with Linear T
    Complexity", Phys. Rev. X 8, 041015 (2018).
[2] G. H. Low and I. L. Chuang, "Hamiltonian Simulation by Qubitization",
    Quantum 3, 163 (2019).

USAGE
-----
    python tools/estimate_ft_resources.py                  # table for the certified suite
    python tools/estimate_ft_resources.py --eps 0.0016     # to chemical accuracy
    python tools/estimate_ft_resources.py --json out.json  # machine-readable
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO / "releases" / "v4" / "db"

# Cost-model constants. Changing one of these changes every number this script
# prints, so they are named, defaulted here, and echoed in the output.
T_PER_TOFFOLI = 4          # measurement-assisted Toffoli; synthesis-only would be 7
COEFF_BITS_MU = 20         # bits of precision for LCU coefficients (alias sampling)

# Precision targets, in Hartree.
EPS_CHEMICAL = 1.6e-3      # chemical accuracy
EPS_CERTIFY = 1.0e-2       # QEncode certification threshold


def load_entries(db_dir: Path):
    for f in sorted(db_dir.glob("*.json")):
        try:
            yield f, json.loads(f.read_text(encoding="utf-8"))
        except Exception as ex:  # a malformed file should not kill the sweep
            print(f"  [WARN] unreadable {f.name}: {ex}", file=sys.stderr)


def hamiltonian_stats(entry: dict):
    """(n_qubits, L, lambda) from the stored Pauli decomposition, or None."""
    ham = (entry.get("artifacts") or {}).get("qubit_hamiltonian") or {}
    terms = ham.get("pauli_terms")
    if not terms:
        return None
    lam = 0.0
    for t in terms:
        try:
            lam += abs(float(t["coefficient"]))
        except (KeyError, TypeError, ValueError):
            return None
    n = ham.get("num_qubits")
    if n is None:
        return None
    return int(n), len(terms), lam


def estimate(n_system: int, n_terms: int, lam: float, eps: float,
             mu: int = COEFF_BITS_MU, t_per_toffoli: int = T_PER_TOFFOLI) -> dict:
    """Qubitized-QPE cost under the model documented at the top of this file."""
    if eps <= 0:
        raise ValueError("eps must be positive")
    walks = math.ceil(math.pi * lam / (2.0 * eps))            # (1)
    toff_per_walk = 2 * n_terms + mu                          # (2)
    toffolis = walks * toff_per_walk
    t_gates = toffolis * t_per_toffoli                        # (3)
    idx = max(1, math.ceil(math.log2(n_terms))) if n_terms > 1 else 1
    logical = n_system + idx + idx + mu + 1                   # (4)
    return {
        "n_system_qubits": n_system,
        "n_pauli_terms": n_terms,
        "lambda_hartree": lam,
        "target_precision_hartree": eps,
        "walk_steps": walks,
        "toffolis_per_walk": toff_per_walk,
        "toffoli_count": toffolis,
        "t_gate_count": t_gates,
        "logical_qubits": logical,
    }


def _fmt(x: float) -> str:
    """Compact magnitude, because these numbers span many orders."""
    if x >= 1e12: return f"{x/1e12:.2f}T"
    if x >= 1e9:  return f"{x/1e9:.2f}G"
    if x >= 1e6:  return f"{x/1e6:.2f}M"
    if x >= 1e3:  return f"{x/1e3:.2f}k"
    return f"{x:.0f}"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Fault-tolerant (qubitized QPE) resource estimates for QEncode entries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db-dir", default=str(DEFAULT_DB))
    ap.add_argument("--eps", type=float, default=EPS_CHEMICAL,
                    help=f"target precision in Hartree (default {EPS_CHEMICAL}, chemical accuracy)")
    ap.add_argument("--mu", type=int, default=COEFF_BITS_MU,
                    help="bits of precision for LCU coefficients")
    ap.add_argument("--t-per-toffoli", type=int, default=T_PER_TOFFOLI, choices=(4, 7))
    ap.add_argument("--all-tiers", action="store_true",
                    help="include research-tier entries as well as certified")
    ap.add_argument("--json", metavar="PATH", help="also write machine-readable output")
    args = ap.parse_args()

    db = Path(args.db_dir)
    if not db.is_dir():
        sys.exit(f"db-dir not found: {db}")

    best: dict[str, dict] = {}   # one row per molecule: the largest Hamiltonian seen
    skipped = 0
    for path, entry in load_entries(db):
        certified = (entry.get("trust") or {}).get("certified_utc") is not None
        if not certified and not args.all_tiers:
            continue
        stats = hamiltonian_stats(entry)
        if stats is None:
            skipped += 1
            continue
        n, L, lam = stats
        mol = (entry.get("problem") or {}).get("molecule") or path.name.split("_ccpvdz")[0]
        row = estimate(n, L, lam, args.eps, args.mu, args.t_per_toffoli)
        row["molecule"] = mol
        # One row per molecule. The Hamiltonian is a property of the molecule and its
        # active space, not of the ansatz, so entries differing only by ansatz give the
        # same estimate; keep the largest term count (the untapered-most encoding).
        if mol not in best or row["n_pauli_terms"] > best[mol]["n_pauli_terms"]:
            best[mol] = row

    if not best:
        sys.exit("No entries with a stored Pauli decomposition were found.")

    rows = sorted(best.values(), key=lambda r: r["toffoli_count"])

    print()
    print("  QEncode — fault-tolerant resource estimates (qubitized QPE)")
    print(f"  target precision {args.eps:g} Ha   |   1 Toffoli = {args.t_per_toffoli} T"
          f"   |   coefficient bits mu = {args.mu}")
    print(f"  {len(rows)} molecules"
          + (f"   ({skipped} entries skipped: no stored Hamiltonian)" if skipped else ""))
    print()
    hdr = "  {:<12}{:>5}{:>9}{:>11}{:>11}{:>11}{:>10}".format(
        "MOLECULE", "QB", "TERMS", "LAMBDA", "TOFFOLI", "T GATES", "LOGICAL")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in rows:
        print("  {:<12}{:>5}{:>9}{:>11.2f}{:>11}{:>11}{:>10}".format(
            r["molecule"], r["n_system_qubits"], r["n_pauli_terms"], r["lambda_hartree"],
            _fmt(r["toffoli_count"]), _fmt(r["t_gate_count"]), r["logical_qubits"]))
    print()
    print("  Estimates under the cost model documented in this file, not measurements")
    print("  and not compiled circuits. Physical qubits and runtime are deliberately")
    print("  not reported: they depend on code distance and error rate, which would")
    print("  dominate the result. See the module docstring for the model and sources.")
    print()

    if args.json:
        payload = {
            "model": {
                "method": "qubitized QPE (LCU over the Pauli decomposition)",
                "walk_steps_formula": "ceil(pi * lambda / (2 * eps))",
                "toffolis_per_walk_formula": "2 * n_pauli_terms + mu",
                "t_per_toffoli": args.t_per_toffoli,
                "coefficient_bits_mu": args.mu,
                "target_precision_hartree": args.eps,
                "references": [
                    "Babbush et al., Phys. Rev. X 8, 041015 (2018)",
                    "Low and Chuang, Quantum 3, 163 (2019)",
                ],
                "caveats": [
                    "Model evaluation, not a measurement or a compiled circuit.",
                    "Physical qubits and wall-clock runtime intentionally omitted.",
                    "Constant factors vary between published cost models.",
                ],
            },
            "estimates": rows,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  Wrote {args.json}")
        print()


if __name__ == "__main__":
    main()
