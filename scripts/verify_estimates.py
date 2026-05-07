#!/usr/bin/env python3
"""
QEncode Suite v2 — Estimate Verification Script
================================================
Runs REAL VQE calculations for CO, NH3, LiF and compares
against Claude's estimates. Prints a side-by-side table.

Install (Ubuntu):
    pip install pyscf==2.5.0 \
                qiskit==1.0.2 \
                qiskit-nature==0.7.2 \
                qiskit-algorithms==0.3.0

Run:
    python verify_estimates.py

Output:
    - Side-by-side comparison table in terminal
    - real_results.json  (full raw output)
    - real_rows_accuracy.csv
    - real_rows_cost.csv
    - real_rows_balanced.csv
"""

import json, csv, warnings, sys
import numpy as np
warnings.filterwarnings("ignore")

# ── My estimates (what Claude generated) ─────────────────────────────────────
ESTIMATES = {
    "CO": [
        # mapping,              ansatz,               gap,           depth, 2q,  baseline
        ("bravyi_kitaev",  "uccsd",              7.832819e-07,  908,  572, False),
        ("parity",         "uccsd",              8.241048e-07,  892,  572, False),
        ("jordan_wigner",  "uccsd",              8.423157e-07,  934,  624, True),
        ("parity",         "hardware_efficient", 2.813479e-03,   27,   56, False),
        ("bravyi_kitaev",  "hardware_efficient", 2.951824e-03,   27,   56, False),
        ("jordan_wigner",  "hardware_efficient", 3.538473e-03,   33,   72, False),
    ],
    "LiF": [
        ("jordan_wigner",  "uccsd",              4.172819e-05,  923,  612, True),
        ("parity",         "uccsd",              4.291048e-05,  887,  558, False),
        ("bravyi_kitaev",  "uccsd",              4.512819e-05,  901,  558, False),
        ("parity",         "hardware_efficient", 6.231479e-03,   27,   56, False),
        ("bravyi_kitaev",  "hardware_efficient", 6.872819e-03,   27,   56, False),
        ("jordan_wigner",  "hardware_efficient", 7.841924e-03,   33,   72, False),
    ],
    "NH3": [
        ("parity",         "uccsd",              1.143282e-06,  904,  574, False),
        ("bravyi_kitaev",  "uccsd",              1.214839e-06,  918,  574, False),
        ("jordan_wigner",  "uccsd",              1.381749e-06,  947,  628, True),
        ("parity",         "hardware_efficient", 3.242817e-03,   27,   56, False),
        ("bravyi_kitaev",  "hardware_efficient", 3.572819e-03,   27,   56, False),
        ("jordan_wigner",  "hardware_efficient", 4.081924e-03,   33,   72, False),
    ],
}

# ── Molecule geometries (equilibrium, Angstrom) ───────────────────────────────
MOLECULES = {
    "CO":  "C 0 0 0; O 0 0 1.128",
    "LiF": "Li 0 0 0; F 0 0 1.5639",
    "NH3": "N 0 0 0.1173; H 0 0.9345 -0.3910; H 0.8094 -0.4672 -0.3910; H -0.8094 -0.4672 -0.3910",
}

# ── Check dependencies ────────────────────────────────────────────────────────
print("Checking dependencies...")
errors = []
try:
    from pyscf import gto, scf, fci
except ImportError:
    errors.append("pyscf")
try:
    from qiskit_nature.second_q.drivers import PySCFDriver
    from qiskit_nature.second_q.mappers import (
        JordanWignerMapper, ParityMapper, BravyiKitaevMapper
    )
    from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
    from qiskit_nature.second_q.algorithms import GroundStateEigensolver
    from qiskit_nature.second_q.transformers import FreezeCoreTransformer
except ImportError:
    errors.append("qiskit-nature==0.7.2")
try:
    from qiskit_algorithms import VQE, NumPyMinimumEigensolver
    from qiskit_algorithms.optimizers import SLSQP
except ImportError:
    errors.append("qiskit-algorithms==0.3.0")
try:
    from qiskit.primitives import Estimator
    from qiskit import transpile
    from qiskit.circuit.library import TwoLocal
except ImportError:
    errors.append("qiskit==1.0.2")

if errors:
    print("\nMissing packages. Run:")
    print(f"  pip install pyscf==2.5.0 {' '.join(errors)}")
    sys.exit(1)
print("All dependencies found.\n")


# ── Helper: run one molecule ──────────────────────────────────────────────────
def run_molecule(name, geometry):
    print(f"\n{'='*60}")
    print(f"  {name}  —  {geometry}")
    print(f"{'='*60}")

    # ── Qiskit Nature driver + freeze core ───────────────────────────────────
    driver = PySCFDriver(atom=geometry, basis="sto-3g", charge=0, spin=0)
    problem = driver.run()
    problem = FreezeCoreTransformer(freeze_core=True).transform(problem)

    n_orb = problem.num_spatial_orbitals
    n_elec = problem.num_particles
    print(f"  Active orbitals: {n_orb}   Active electrons: {n_elec}")

    # ── Mappers ──────────────────────────────────────────────────────────────
    mappers = {
        "jordan_wigner": JordanWignerMapper(),
        "parity":        ParityMapper(num_particles=n_elec),
        "bravyi_kitaev": BravyiKitaevMapper(),
    }

    # ── Exact ground state per mapping ───────────────────────────────────────
    numpy_energies = {}
    for mname, mapper in mappers.items():
        solver = GroundStateEigensolver(mapper, NumPyMinimumEigensolver())
        result = solver.solve(problem)
        numpy_energies[mname] = result.total_energies[0].real
    print(f"  Exact (JW):      {numpy_energies['jordan_wigner']:.8f} Ha")

    # ── VQE UCCSD ────────────────────────────────────────────────────────────
    uccsd_results = {}
    for mname, mapper in mappers.items():
        print(f"  UCCSD [{mname}]...", flush=True)
        hf_state = HartreeFock(n_orb, n_elec, mapper)
        ansatz   = UCCSD(n_orb, n_elec, mapper, initial_state=hf_state, reps=1)
        qubit_op = mapper.map(problem.second_q_ops()[0])

        vqe    = VQE(Estimator(), ansatz, SLSQP(maxiter=500))
        result = vqe.compute_minimum_eigenvalue(qubit_op)

        e_vqe   = result.eigenvalue.real + problem.nuclear_repulsion_energy
        gap     = abs(e_vqe - numpy_energies[mname])
        bound   = ansatz.assign_parameters(result.optimal_parameters)
        circ    = transpile(bound, basis_gates=["cx", "u"], optimization_level=3)
        depth   = circ.depth()
        twoq    = circ.count_ops().get("cx", 0)
        bscore  = gap * depth

        uccsd_results[mname] = dict(gap=gap, depth=depth, twoq=twoq, bscore=bscore)
        print(f"    gap={gap:.4e}  depth={depth}  2Q={twoq}  score={bscore:.4e}")

    # ── VQE Hardware-Efficient (TwoLocal, reps=2, linear) ────────────────────
    hea_results = {}
    for mname, mapper in mappers.items():
        print(f"  HEA    [{mname}]...", flush=True)
        qubit_op = mapper.map(problem.second_q_ops()[0])
        n_q      = qubit_op.num_qubits
        hea      = TwoLocal(n_q, ["ry","rz"], "cx", entanglement="linear", reps=2)

        vqe    = VQE(Estimator(), hea, SLSQP(maxiter=1000))
        result = vqe.compute_minimum_eigenvalue(qubit_op)

        e_vqe  = result.eigenvalue.real + problem.nuclear_repulsion_energy
        gap    = abs(e_vqe - numpy_energies[mname])
        bound  = hea.assign_parameters(result.optimal_parameters)
        circ   = transpile(bound, basis_gates=["cx", "u"], optimization_level=3)
        depth  = circ.depth()
        twoq   = circ.count_ops().get("cx", 0)
        bscore = gap * depth

        hea_results[mname] = dict(gap=gap, depth=depth, twoq=twoq, bscore=bscore)
        print(f"    gap={gap:.4e}  depth={depth}  2Q={twoq}  score={bscore:.4e}")

    return {
        "uccsd": uccsd_results,
        "hea":   hea_results,
    }


# ── Run all three molecules ───────────────────────────────────────────────────
real_results = {}
for mol_name, geometry in MOLECULES.items():
    real_results[mol_name] = run_molecule(mol_name, geometry)


# ── Build comparison table ────────────────────────────────────────────────────
def compare_table(mol_name):
    real  = real_results[mol_name]
    est   = {(m, a): (g, d, q) for m, a, g, d, q, _ in ESTIMATES[mol_name]}

    rows = []
    for mname in ["jordan_wigner", "parity", "bravyi_kitaev"]:
        for ansatz_key, res_dict in [("uccsd", real["uccsd"]), ("hardware_efficient", real["hea"])]:
            r   = res_dict[mname]
            key = (mname, ansatz_key)
            e_gap, e_depth, e_twoq = est.get(key, (None, None, None))
            e_score = (e_gap * e_depth) if e_gap and e_depth else None

            rows.append({
                "mapping":   mname,
                "ansatz":    ansatz_key,
                "est_gap":   e_gap,
                "real_gap":  r["gap"],
                "est_depth": e_depth,
                "real_depth":r["depth"],
                "est_2q":    e_twoq,
                "real_2q":   r["twoq"],
                "est_score": e_score,
                "real_score":r["bscore"],
            })
    return rows


def pct_err(est, real):
    if est is None or real is None or real == 0:
        return "—"
    return f"{abs(est - real) / real * 100:.0f}%"


print("\n\n" + "=" * 100)
print("  COMPARISON TABLE — ESTIMATED vs REAL")
print("=" * 100)

all_leaderboard_rows = []

for mol_name in ["CO", "LiF", "NH3"]:
    rows = compare_table(mol_name)
    header = (
        f"\n  {mol_name}\n"
        f"  {'Mapping':<22} {'Ansatz':<20} "
        f"{'Est Gap':>12} {'Real Gap':>12} {'Err':>6}  "
        f"{'Est D':>6} {'Real D':>6} {'Err':>6}  "
        f"{'Est 2Q':>6} {'Real 2Q':>6} {'Err':>6}  "
        f"{'Est Score':>12} {'Real Score':>12} {'Err':>6}"
    )
    print(header)
    print("  " + "-" * 96)

    for r in rows:
        print(
            f"  {r['mapping']:<22} {r['ansatz']:<20} "
            f"{r['est_gap']:>12.3e} {r['real_gap']:>12.3e} {pct_err(r['est_gap'], r['real_gap']):>6}  "
            f"{r['est_depth']:>6} {r['real_depth']:>6} {pct_err(r['est_depth'], r['real_depth']):>6}  "
            f"{r['est_2q']:>6} {r['real_2q']:>6} {pct_err(r['est_2q'], r['real_2q']):>6}  "
            f"{r['est_score']:>12.3e} {r['real_score']:>12.3e} {pct_err(r['est_score'], r['real_score']):>6}"
        )

        all_leaderboard_rows.append({
            "molecule": mol_name,
            "mapping":  r["mapping"],
            "ansatz":   r["ansatz"],
            "real_gap": r["real_gap"],
            "real_depth": r["real_depth"],
            "real_2q":  r["real_2q"],
            "real_score": r["real_score"],
        })


# ── Save outputs ──────────────────────────────────────────────────────────────
with open("real_results.json", "w") as f:
    json.dump(real_results, f, indent=2)

# Accuracy CSV (sorted by gap per molecule)
acc_rows = []
for mol_name in ["CO", "LiF", "NH3"]:
    mol_rows = [r for r in all_leaderboard_rows if r["molecule"] == mol_name]
    mol_rows.sort(key=lambda x: x["real_gap"])
    for i, r in enumerate(mol_rows):
        acc_rows.append([i+1, r["molecule"], r["mapping"], r["ansatz"],
                         r["real_gap"], r["real_depth"], r["real_2q"], False])

with open("real_rows_accuracy.csv", "w", newline="") as f:
    csv.writer(f).writerows(acc_rows)

# Hardware cost CSV (sorted by 2q then depth per molecule)
cost_rows = []
for mol_name in ["CO", "LiF", "NH3"]:
    mol_rows = [r for r in all_leaderboard_rows if r["molecule"] == mol_name]
    mol_rows.sort(key=lambda x: (x["real_2q"], x["real_depth"]))
    for i, r in enumerate(mol_rows):
        cost_rows.append([i+1, r["molecule"], r["mapping"], r["ansatz"],
                          r["real_gap"], r["real_depth"], r["real_2q"], False])

with open("real_rows_cost.csv", "w", newline="") as f:
    csv.writer(f).writerows(cost_rows)

# Balanced CSV (sorted by score per molecule)
bal_rows = []
for mol_name in ["CO", "LiF", "NH3"]:
    mol_rows = [r for r in all_leaderboard_rows if r["molecule"] == mol_name]
    mol_rows.sort(key=lambda x: x["real_score"])
    for i, r in enumerate(mol_rows):
        bal_rows.append([i+1, r["molecule"], r["mapping"], r["ansatz"],
                         r["real_gap"], r["real_depth"], r["real_2q"],
                         r["real_score"], False])

with open("real_rows_balanced.csv", "w", newline="") as f:
    csv.writer(f).writerows(bal_rows)

print("\n\nFiles saved:")
print("  real_results.json")
print("  real_rows_accuracy.csv")
print("  real_rows_cost.csv")
print("  real_rows_balanced.csv")
print("\nSend these back and I will replace the estimated data with the real values.")
