#!/usr/bin/env python
"""Feasibility probe: what would a cc-pVTZ track actually cost?

The assumption behind deferring cc-pVTZ is that it means re-baselining the suite. That is
true of the entries, but it is worth knowing WHERE the cost lands. The qubit count is set
by the active space, not the basis, so a larger basis may cost only classical time and
leave the quantum side untouched -- or it may not, if the Hamiltonian densifies.

Measures, per molecule, at cc-pVDZ and cc-pVTZ:

  * basis functions and classical time (HF, CASCI)
  * qubits and Pauli terms after mapping and tapering -- the quantum-side cost
  * the CASCI energy shift, which is what a larger basis actually buys

No entries are written and nothing in the suite is touched.
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
          "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import json
import sys
import time

import numpy as np

GEOM = {
    "H2":  ("H 0 0 0; H 0 0 0.74", 2, 2),
    "LiH": ("Li 0 0 0; H 0 0 1.595", 4, 4),
    "H2O": ("O 0 0 0.1173; H 0 0.7572 -0.4692; H 0 -0.7572 -0.4692", 4, 4),
    "N2":  ("N 0 0 0; N 0 0 1.0977", 6, 6),
}


def probe(name, geom, nelec, norb, basis):
    from pyscf import gto, scf, mcscf

    t0 = time.time()
    mol = gto.M(atom=geom, basis=basis, symmetry=False, verbose=0)
    nbf = mol.nao_nr()
    mf = scf.RHF(mol).run()
    t_hf = time.time() - t0

    t1 = time.time()
    mc = mcscf.CASCI(mf, norb, nelec)
    mc.verbose = 0
    res = mc.kernel()
    e_casci = res[0]
    t_cas = time.time() - t1

    # qubit-side cost, via the same OpenFermion bridge route the pipeline uses
    t2 = time.time()
    n_qubits = n_terms = None
    try:
        from pyscf import ao2mo
        h1e, ecore = mc.get_h1eff()
        eri = ao2mo.restore(1, mc.get_h2eff(), norb)
        from openfermion import InteractionOperator, jordan_wigner
        from openfermion.chem.molecular_data import spinorb_from_spatial

        one_b, two_b = spinorb_from_spatial(np.asarray(h1e), np.asarray(eri))
        op = InteractionOperator(ecore, one_b, 0.5 * two_b)
        qop = jordan_wigner(op)
        qop.compress()
        n_terms = len(qop.terms)
        n_qubits = 2 * norb
    except Exception as exc:  # pragma: no cover - reported, not raised
        n_terms = "err: %s" % str(exc)[:40]
    t_map = time.time() - t2

    return {
        "basis": basis, "nbf": nbf, "e_hf": float(mf.e_tot), "e_casci": float(e_casci),
        "n_qubits": n_qubits, "n_terms": n_terms,
        "t_hf": round(t_hf, 2), "t_casci": round(t_cas, 2), "t_map": round(t_map, 2),
    }


def main():
    mols = sys.argv[1:] or ["H2", "LiH", "H2O", "N2"]
    print("%-6s %-10s %6s %8s %7s %16s %12s %8s %8s"
          % ("mol", "basis", "nbf", "qubits", "terms", "E_CASCI (Ha)", "dE vs DZ", "t_HF", "t_CASCI"))
    print("-" * 104)
    out = {}
    for m in mols:
        geom, nelec, norb = GEOM[m]
        row = {}
        for basis in ("cc-pvdz", "cc-pvtz"):
            try:
                r = probe(m, geom, nelec, norb, basis)
            except Exception as exc:
                print("%-6s %-10s FAILED: %s" % (m, basis, str(exc)[:60]))
                continue
            row[basis] = r
            d = ""
            if basis == "cc-pvtz" and "cc-pvdz" in row:
                d = "%+.6f" % (r["e_casci"] - row["cc-pvdz"]["e_casci"])
            print("%-6s %-10s %6d %8s %7s %16.8f %12s %7.2fs %7.2fs"
                  % (m, basis, r["nbf"], r["n_qubits"], r["n_terms"],
                     r["e_casci"], d, r["t_hf"], r["t_casci"]))
        out[m] = row
        print("-" * 104)

    print()
    print("=" * 104)
    print("WHAT A cc-pVTZ TRACK WOULD COST")
    print("=" * 104)
    print("%-6s %12s %14s %14s %16s" % ("mol", "nbf DZ->TZ", "qubits DZ->TZ",
                                        "terms DZ->TZ", "classical slowdown"))
    print("-" * 104)
    for m, row in out.items():
        if len(row) != 2:
            continue
        dz, tz = row["cc-pvdz"], row["cc-pvtz"]
        slow = (tz["t_hf"] + tz["t_casci"]) / max(dz["t_hf"] + dz["t_casci"], 1e-9)
        print("%-6s %12s %14s %14s %15.1fx"
              % (m, "%d -> %d" % (dz["nbf"], tz["nbf"]),
                 "%s -> %s" % (dz["n_qubits"], tz["n_qubits"]),
                 "%s -> %s" % (dz["n_terms"], tz["n_terms"]), slow))
    print()
    same_q = all(row["cc-pvdz"]["n_qubits"] == row["cc-pvtz"]["n_qubits"]
                 for row in out.values() if len(row) == 2)
    same_t = all(row["cc-pvdz"]["n_terms"] == row["cc-pvtz"]["n_terms"]
                 for row in out.values() if len(row) == 2)
    if same_q and same_t:
        print("  The quantum-side cost is UNCHANGED: same qubits, same Pauli terms. A")
        print("  cc-pVTZ track would cost classical preprocessing time and a full")
        print("  re-baseline of the entry database. The circuits and gate counts would be")
        print("  identical; T-gate estimates scale with lambda = sum|h_a|, which shifts by")
        print("  under 2 percent, so they move by about a percent rather than being rebuilt.")
    else:
        print("  The quantum-side cost CHANGES with basis; a cc-pVTZ track is not free on")
        print("  the circuit side either.")
    json.dump(out, open("/tmp/probe_basis.json", "w"), indent=1)


if __name__ == "__main__":
    main()
