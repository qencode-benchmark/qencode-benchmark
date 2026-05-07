#!/usr/bin/env python3
"""
QEncode Suite v2 — Estimate Verification Script (v2, fixed)
============================================================
Runs REAL calculations for CO, NH3, LiF and prints a side-by-side
comparison table against Claude's estimates.

Uses PySCF for all chemistry (avoids scipy/qiskit version conflicts).
Uses Qiskit only for circuit building + transpilation (gate counts).

Install (Ubuntu — use versions already in your env):
    pip install pyscf qiskit qiskit-nature qiskit-algorithms

Run:
    python verify_estimates.py

Output:
    real_results.json
    real_rows_accuracy.csv
    real_rows_cost.csv
    real_rows_balanced.csv
"""

import json, csv, warnings, sys
import numpy as np
from scipy.optimize import minimize
warnings.filterwarnings("ignore")

# ── Claude's estimates ────────────────────────────────────────────────────────
ESTIMATES = {
    "CO": [
        ("bravyi_kitaev",  "uccsd",              7.832819e-07,  908, 572, False),
        ("parity",         "uccsd",              8.241048e-07,  892, 572, False),
        ("jordan_wigner",  "uccsd",              8.423157e-07,  934, 624, True),
        ("parity",         "hardware_efficient", 2.813479e-03,   27,  56, False),
        ("bravyi_kitaev",  "hardware_efficient", 2.951824e-03,   27,  56, False),
        ("jordan_wigner",  "hardware_efficient", 3.538473e-03,   33,  72, False),
    ],
    "LiF": [
        ("jordan_wigner",  "uccsd",              4.172819e-05,  923, 612, True),
        ("parity",         "uccsd",              4.291048e-05,  887, 558, False),
        ("bravyi_kitaev",  "uccsd",              4.512819e-05,  901, 558, False),
        ("parity",         "hardware_efficient", 6.231479e-03,   27,  56, False),
        ("bravyi_kitaev",  "hardware_efficient", 6.872819e-03,   27,  56, False),
        ("jordan_wigner",  "hardware_efficient", 7.841924e-03,   33,  72, False),
    ],
    "NH3": [
        ("parity",         "uccsd",              1.143282e-06,  904, 574, False),
        ("bravyi_kitaev",  "uccsd",              1.214839e-06,  918, 574, False),
        ("jordan_wigner",  "uccsd",              1.381749e-06,  947, 628, True),
        ("parity",         "hardware_efficient", 3.242817e-03,   27,  56, False),
        ("bravyi_kitaev",  "hardware_efficient", 3.572819e-03,   27,  56, False),
        ("jordan_wigner",  "hardware_efficient", 4.081924e-03,   33,  72, False),
    ],
}

# ── Molecule definitions ──────────────────────────────────────────────────────
MOLECULES = {
    "CO":  dict(atom="C 0 0 0; O 0 0 1.128",    basis="sto-3g", charge=0, spin=0),
    "LiF": dict(atom="Li 0 0 0; F 0 0 1.5639",  basis="sto-3g", charge=0, spin=0),
    "NH3": dict(atom="N 0 0 0.1173; H 0 0.9345 -0.3910; H 0.8094 -0.4672 -0.3910; H -0.8094 -0.4672 -0.3910",
                basis="sto-3g", charge=0, spin=0),
}

# ── Check deps ────────────────────────────────────────────────────────────────
print("Checking dependencies...")
errors = []
try:
    from pyscf import gto, scf, fci, cc, mcscf, ao2mo
    print("  pyscf          OK")
except ImportError:
    errors.append("pyscf"); print("  pyscf          MISSING")

try:
    from qiskit_nature.second_q.drivers import PySCFDriver
    from qiskit_nature.second_q.mappers import JordanWignerMapper, ParityMapper, BravyiKitaevMapper
    from qiskit_nature.second_q.circuit.library import UCCSD, HartreeFock
    from qiskit_nature.second_q.transformers import FreezeCoreTransformer
    print("  qiskit-nature  OK")
except ImportError as e:
    errors.append("qiskit-nature"); print(f"  qiskit-nature  MISSING ({e})")

try:
    from qiskit import transpile
    from qiskit.circuit.library import TwoLocal
    print("  qiskit         OK")
except ImportError as e:
    errors.append("qiskit"); print(f"  qiskit         MISSING ({e})")

if errors:
    print(f"\nInstall missing: pip install {' '.join(errors)}")
    sys.exit(1)
print()


# ── Step 1: PySCF classical reference ────────────────────────────────────────
def pyscf_reference(name, mol_kwargs):
    """Returns (e_hf, e_fci, e_ccsd, n_active_e, n_active_o, active_space_e_fci)"""
    mol = gto.Mole()
    mol.atom   = mol_kwargs["atom"]
    mol.basis  = mol_kwargs["basis"]
    mol.charge = mol_kwargs["charge"]
    mol.spin   = mol_kwargs["spin"]
    mol.verbose = 0
    mol.build()

    mf = scf.RHF(mol)
    e_hf = mf.kernel()

    # Full FCI
    ci = fci.FCI(mf)
    ci.verbose = 0
    e_fci, _ = ci.kernel()

    # CCSD (classical equivalent of UCCSD at convergence for single-reference)
    mycc = cc.CCSD(mf)
    mycc.verbose = 0
    mycc.kernel()
    e_ccsd = e_hf + mycc.e_corr

    # Active space: freeze core (innermost occupied orbitals, 1 per heavy atom)
    n_heavy = sum(1 for a in mol.atom_charges() if a > 1)
    n_frozen = n_heavy
    n_occ    = mol.nelectron // 2
    n_ao     = mol.nao_nr()
    n_active_o = n_ao - n_frozen
    n_active_e = mol.nelectron - 2 * n_frozen

    mc_ci = mcscf.CASCI(mf, n_active_o, n_active_e)
    mc_ci.verbose = 0
    e_cas_fci = mc_ci.kernel()[0]

    return dict(
        e_hf=e_hf, e_fci=e_fci, e_ccsd=e_ccsd,
        n_active_e=n_active_e, n_active_o=n_active_o,
        e_cas_fci=e_cas_fci,
        ccsd_gap=abs(e_ccsd - e_fci),
    )


# ── Step 2: Circuit metrics via Qiskit ───────────────────────────────────────
def circuit_metrics(name, mol_kwargs):
    """Build UCCSD and HEA circuits per mapping, transpile, return gate counts."""
    driver  = PySCFDriver(
        atom=mol_kwargs["atom"], basis=mol_kwargs["basis"],
        charge=mol_kwargs["charge"], spin=mol_kwargs["spin"]
    )
    problem = driver.run()
    problem = FreezeCoreTransformer(freeze_core=True).transform(problem)

    n_orb  = problem.num_spatial_orbitals
    n_elec = problem.num_particles
    print(f"    Active space: [{sum(n_elec) if isinstance(n_elec, tuple) else n_elec}e, {n_orb}o]")

    mappers = {
        "jordan_wigner": JordanWignerMapper(),
        "parity":        ParityMapper(num_particles=n_elec),
        "bravyi_kitaev": BravyiKitaevMapper(),
    }

    metrics = {}
    for mname, mapper in mappers.items():
        # ── UCCSD circuit ──────────────────────────────────────────────────
        hf_state = HartreeFock(n_orb, n_elec, mapper)
        uccsd    = UCCSD(n_orb, n_elec, mapper, initial_state=hf_state, reps=1)

        # Bind all params to 0 just to get the unoptimised circuit structure
        # (actual depth is parameter-independent for UCCSD at reps=1)
        from qiskit.circuit import ParameterVector
        params = uccsd.parameters
        bound  = uccsd.assign_parameters({p: 0.01 for p in params})
        t_uccsd = transpile(bound, basis_gates=["cx","u"], optimization_level=1)
        uccsd_depth = t_uccsd.depth()
        uccsd_2q    = t_uccsd.count_ops().get("cx", 0)

        # ── HEA circuit ────────────────────────────────────────────────────
        qubit_op = mapper.map(problem.second_q_ops()[0])
        n_q      = qubit_op.num_qubits
        hea      = TwoLocal(n_q, ["ry","rz"], "cx", entanglement="linear", reps=2)
        params_h = hea.parameters
        bound_h  = hea.assign_parameters({p: 0.01 for p in params_h})
        t_hea    = transpile(bound_h, basis_gates=["cx","u"], optimization_level=1)
        hea_depth = t_hea.depth()
        hea_2q    = t_hea.count_ops().get("cx", 0)

        metrics[mname] = dict(
            uccsd_depth=uccsd_depth, uccsd_2q=uccsd_2q,
            hea_depth=hea_depth,    hea_2q=hea_2q,
            n_qubits=n_q,
        )
        print(f"    {mname:20s}  UCCSD d={uccsd_depth} 2Q={uccsd_2q}  |  HEA d={hea_depth} 2Q={hea_2q}")

    return metrics, n_orb, n_elec


# ── Step 3: VQE energies (statevector, exact) ─────────────────────────────────
def vqe_energies(name, mol_kwargs):
    """Run exact statevector VQE for gap computation."""
    try:
        from qiskit_algorithms import VQE
        from qiskit_algorithms.optimizers import SLSQP
        from qiskit.primitives import Estimator
    except ImportError:
        print("    qiskit-algorithms not available — using CCSD gap as UCCSD proxy")
        return None

    driver  = PySCFDriver(
        atom=mol_kwargs["atom"], basis=mol_kwargs["basis"],
        charge=mol_kwargs["charge"], spin=mol_kwargs["spin"]
    )
    problem = driver.run()
    problem = FreezeCoreTransformer(freeze_core=True).transform(problem)
    n_orb   = problem.num_spatial_orbitals
    n_elec  = problem.num_particles

    mappers = {
        "jordan_wigner": JordanWignerMapper(),
        "parity":        ParityMapper(num_particles=n_elec),
        "bravyi_kitaev": BravyiKitaevMapper(),
    }

    # Exact reference via sparse diag (avoid scipy .H issue)
    exact_energies = {}
    for mname, mapper in mappers.items():
        qubit_op = mapper.map(problem.second_q_ops()[0])
        try:
            from qiskit.quantum_info import SparsePauliOp
            mat = qubit_op.to_matrix()
            eigvals = np.linalg.eigvalsh(mat)
            exact_e = eigvals[0] + problem.nuclear_repulsion_energy
            exact_energies[mname] = exact_e
        except Exception as e:
            print(f"    Exact diag failed for {mname}: {e}")
            exact_energies[mname] = None

    results = {}
    for mname, mapper in mappers.items():
        qubit_op = mapper.map(problem.second_q_ops()[0])
        hf_state = HartreeFock(n_orb, n_elec, mapper)

        # UCCSD VQE
        print(f"    VQE UCCSD [{mname}]...", flush=True)
        uccsd = UCCSD(n_orb, n_elec, mapper, initial_state=hf_state, reps=1)
        try:
            vqe = VQE(Estimator(), uccsd, SLSQP(maxiter=500))
            res = vqe.compute_minimum_eigenvalue(qubit_op)
            e_vqe = res.eigenvalue.real + problem.nuclear_repulsion_energy
            gap_u = abs(e_vqe - exact_energies[mname]) if exact_energies[mname] else None
        except Exception as e:
            print(f"      VQE failed: {e}")
            gap_u = None

        # HEA VQE
        print(f"    VQE HEA   [{mname}]...", flush=True)
        n_q = qubit_op.num_qubits
        hea = TwoLocal(n_q, ["ry","rz"], "cx", entanglement="linear", reps=2)
        try:
            vqe_h = VQE(Estimator(), hea, SLSQP(maxiter=1000))
            res_h = vqe_h.compute_minimum_eigenvalue(qubit_op)
            e_hea = res_h.eigenvalue.real + problem.nuclear_repulsion_energy
            gap_h = abs(e_hea - exact_energies[mname]) if exact_energies[mname] else None
        except Exception as e:
            print(f"      HEA VQE failed: {e}")
            gap_h = None

        results[mname] = dict(uccsd_gap=gap_u, hea_gap=gap_h)
        if gap_u: print(f"      UCCSD gap={gap_u:.4e}  HEA gap={gap_h:.4e}")

    return results


# ── Run all molecules ─────────────────────────────────────────────────────────
all_real = {}

for mol_name, mol_kwargs in MOLECULES.items():
    print(f"\n{'='*60}")
    print(f"  {mol_name}")
    print(f"{'='*60}")

    print("  [1/3] PySCF classical reference...")
    chem = pyscf_reference(mol_name, mol_kwargs)
    print(f"    HF:        {chem['e_hf']:.8f} Ha")
    print(f"    FCI:       {chem['e_fci']:.8f} Ha")
    print(f"    CCSD:      {chem['e_ccsd']:.8f} Ha")
    print(f"    CCSD gap:  {chem['ccsd_gap']:.4e} Ha  (proxy for UCCSD)")
    print(f"    CAS-FCI:   {chem['e_cas_fci']:.8f} Ha  ([{chem['n_active_e']}e,{chem['n_active_o']}o])")

    print("  [2/3] Circuit metrics (transpilation)...")
    circ, n_orb, n_elec = circuit_metrics(mol_name, mol_kwargs)

    print("  [3/3] VQE energies (statevector simulation)...")
    gaps = vqe_energies(mol_name, mol_kwargs)

    all_real[mol_name] = dict(chem=chem, circuits=circ, gaps=gaps)


# ── Comparison table ──────────────────────────────────────────────────────────
def pct(est, real):
    if est is None or real is None or real == 0: return "  —  "
    return f"{abs(est-real)/real*100:5.0f}%"

print("\n\n" + "="*110)
print("  COMPARISON TABLE — Claude's ESTIMATES vs REAL")
print("="*110)
print(f"  {'Mol':<5} {'Mapping':<22} {'Ansatz':<20} "
      f"{'Est Gap':>11} {'Real Gap':>11} {'Err':>6}  "
      f"{'EstD':>5} {'RealD':>5} {'Err':>6}  "
      f"{'Est2Q':>5} {'R2Q':>5} {'Err':>6}")
print("  "+"-"*105)

leaderboard_rows = []

for mol_name in ["CO","LiF","NH3"]:
    real  = all_real[mol_name]
    circ  = real["circuits"]
    gaps  = real["gaps"]
    est_lookup = {(m,a): (g,d,q) for m,a,g,d,q,_ in ESTIMATES[mol_name]}

    for mname in ["jordan_wigner","parity","bravyi_kitaev"]:
        c = circ[mname]
        for ansatz_key in ["uccsd","hardware_efficient"]:
            eg, ed, eq = est_lookup.get((mname, ansatz_key), (None,None,None))

            if ansatz_key == "uccsd":
                rd = c["uccsd_depth"]; rq = c["uccsd_2q"]
                rg = gaps[mname]["uccsd_gap"] if gaps and gaps[mname] else None
            else:
                rd = c["hea_depth"];   rq = c["hea_2q"]
                rg = gaps[mname]["hea_gap"] if gaps and gaps[mname] else None

            rs = (rg * rd) if rg and rd else None
            es = (eg * ed) if eg and ed else None

            print(f"  {mol_name:<5} {mname:<22} {ansatz_key:<20} "
                  f"{eg:>11.3e} "
                  f"{(f'{rg:.3e}' if rg else '  PENDING'):>11} {pct(eg,rg):>6}  "
                  f"{ed:>5} {rd:>5} {pct(ed,rd):>6}  "
                  f"{eq:>5} {rq:>5} {pct(eq,rq):>6}")

            leaderboard_rows.append(dict(
                molecule=mol_name, mapping=mname, ansatz=ansatz_key,
                est_gap=eg, real_gap=rg,
                est_depth=ed, real_depth=rd,
                est_2q=eq, real_2q=rq,
                est_score=es, real_score=rs,
            ))


# ── Save outputs ──────────────────────────────────────────────────────────────
with open("real_results.json","w") as f:
    # Convert non-serializable floats
    def clean(o):
        if isinstance(o, np.floating): return float(o)
        if isinstance(o, np.integer):  return int(o)
        if isinstance(o, dict): return {k: clean(v) for k,v in o.items()}
        if isinstance(o, (list,tuple)): return [clean(i) for i in o]
        return o
    json.dump(clean(all_real), f, indent=2)

for mol_name in ["CO","LiF","NH3"]:
    rows = [r for r in leaderboard_rows if r["molecule"]==mol_name]

    acc = sorted(rows, key=lambda r: r["real_gap"] or 1e99)
    with open(f"real_{mol_name}_accuracy.csv","w",newline="") as f:
        w = csv.writer(f)
        for i,r in enumerate(acc):
            w.writerow([i+1, r["molecule"], r["mapping"], r["ansatz"],
                        r["real_gap"], r["real_depth"], r["real_2q"], False])

    cost = sorted(rows, key=lambda r: (r["real_2q"] or 9999, r["real_depth"] or 9999))
    with open(f"real_{mol_name}_cost.csv","w",newline="") as f:
        w = csv.writer(f)
        for i,r in enumerate(cost):
            w.writerow([i+1, r["molecule"], r["mapping"], r["ansatz"],
                        r["real_gap"], r["real_depth"], r["real_2q"], False])

    bal = sorted(rows, key=lambda r: r["real_score"] or 1e99)
    with open(f"real_{mol_name}_balanced.csv","w",newline="") as f:
        w = csv.writer(f)
        for i,r in enumerate(bal):
            w.writerow([i+1, r["molecule"], r["mapping"], r["ansatz"],
                        r["real_gap"], r["real_depth"], r["real_2q"],
                        r["real_score"], False])

print("\n\nSaved: real_results.json + real_CO/LiF/NH3_accuracy/cost/balanced.csv")
print("Send real_results.json back to Claude to update the leaderboard.")
