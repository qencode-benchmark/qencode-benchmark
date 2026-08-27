#!/usr/bin/env python
"""Feasibility probe: could a transition-metal system be CERTIFIED, not merely run?

Running one is easy. The question is whether it would produce a certified entry or a
research-tier one, because the certified count is the credibility signal and diluting it
with systems nothing can solve would cost more than it buys.

Three diagnostics, all classical and all cheap:

  T1 diagnostic      CCSD amplitude norm. Above ~0.02 the single-reference picture is
                     breaking down, which is the regime UCCSD and hardware-efficient
                     ansatze are worst at.
  leading weight     largest CI coefficient squared in the CASCI wavefunction. Near 1 the
                     state is essentially one determinant and easy; well below it, the
                     state is a genuine superposition and a shallow ansatz will struggle.
  HF/CASSCF converged  whether the classical reference can even be obtained. A transition
                     metal that will not converge classically cannot anchor a benchmark.

Nothing is written to the entry database.
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
          "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import sys
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore")

# Small, standard transition-metal test systems, plus two main-group controls already in
# the suite so the diagnostics can be read against something known.
SYSTEMS = {
    "ScH":  ("Sc 0 0 0; H 0 0 1.775", 0, 1, (4, 4)),
    "TiO":  ("Ti 0 0 0; O 0 0 1.620", 0, 3, (6, 6)),
    "CuH":  ("Cu 0 0 0; H 0 0 1.463", 0, 1, (4, 4)),
    "CrH":  ("Cr 0 0 0; H 0 0 1.655", 0, 6, (6, 6)),
    # controls
    "N2":   ("N 0 0 0; N 0 0 1.0977", 0, 1, (6, 6)),
    "H2O":  ("O 0 0 0.1173; H 0 0.7572 -0.4692; H 0 -0.7572 -0.4692", 0, 1, (4, 4)),
}


def probe(name, geom, charge, spin, cas, basis="cc-pvdz"):
    from pyscf import gto, scf, mcscf, cc

    out = {"system": name, "basis": basis, "spin": spin, "cas": cas}
    t0 = time.time()
    try:
        mol = gto.M(atom=geom, basis=basis, charge=charge, spin=spin - 1,
                    symmetry=False, verbose=0)
    except Exception as exc:
        out["status"] = "geometry/basis failed: %s" % str(exc)[:60]
        return out
    out["nbf"] = int(mol.nao_nr())
    out["n_elec"] = int(mol.nelectron)

    mf = scf.RHF(mol) if spin == 1 else scf.ROHF(mol)
    mf.max_cycle = 200
    try:
        mf.kernel()
    except Exception as exc:
        out["status"] = "HF crashed: %s" % str(exc)[:50]
        return out
    out["hf_converged"] = bool(mf.converged)
    out["e_hf"] = float(mf.e_tot)
    out["t_hf"] = round(time.time() - t0, 2)

    # T1 diagnostic
    t1 = time.time()
    try:
        mycc = cc.CCSD(mf)
        mycc.max_cycle = 100
        mycc.kernel()
        out["ccsd_converged"] = bool(mycc.converged)
        t1amp = mycc.t1
        if isinstance(t1amp, (list, tuple)):
            n = sum(int(np.asarray(a).size) for a in t1amp)
            nrm = float(np.sqrt(sum(float(np.linalg.norm(np.asarray(a))) ** 2 for a in t1amp)))
        else:
            n = int(np.asarray(t1amp).size)
            nrm = float(np.linalg.norm(np.asarray(t1amp)))
        out["t1_diagnostic"] = nrm / np.sqrt(max(out["n_elec"], 1))
    except Exception as exc:
        out["t1_diagnostic"] = None
        out["ccsd_note"] = str(exc)[:50]
    out["t_ccsd"] = round(time.time() - t1, 2)

    # CASCI leading determinant weight
    t2 = time.time()
    try:
        ne, no = cas
        mc = mcscf.CASCI(mf, no, ne)
        mc.verbose = 0
        e = mc.kernel()[0]
        out["e_casci"] = float(e)
        ci = np.asarray(mc.ci).ravel()
        w = ci ** 2
        out["leading_weight"] = float(w.max())
        out["n_dets_90pct"] = int(np.searchsorted(np.cumsum(np.sort(w)[::-1]), 0.90) + 1)
    except Exception as exc:
        out["leading_weight"] = None
        out["casci_note"] = str(exc)[:50]
    out["t_casci"] = round(time.time() - t2, 2)
    out["status"] = "ok"
    return out


def main():
    names = sys.argv[1:] or list(SYSTEMS)
    rows = []
    for nm in names:
        if nm not in SYSTEMS:
            print("unknown system", nm)
            continue
        geom, chg, spin, cas = SYSTEMS[nm]
        r = probe(nm, geom, chg, spin, cas)
        rows.append(r)
        print("  probed %-5s %s" % (nm, r.get("status", "?")))

    print()
    print("=" * 106)
    print("TRANSITION-METAL FEASIBILITY  (main-group controls at the bottom)")
    print("=" * 106)
    print("%-6s %5s %6s %6s %8s %9s %13s %10s %8s"
          % ("system", "nbf", "elec", "HF ok", "CCSD ok", "T1 diag", "leading wt", "dets>90%", "t_total"))
    print("-" * 106)
    for r in rows:
        if r.get("status") != "ok":
            print("%-6s  %s" % (r["system"], r.get("status")))
            continue
        t = (r.get("t_hf", 0) or 0) + (r.get("t_ccsd", 0) or 0) + (r.get("t_casci", 0) or 0)
        t1 = r.get("t1_diagnostic")
        lw = r.get("leading_weight")
        print("%-6s %5d %6d %6s %8s %9s %13s %10s %7.1fs"
              % (r["system"], r.get("nbf", 0), r.get("n_elec", 0),
                 "yes" if r.get("hf_converged") else "NO",
                 "yes" if r.get("ccsd_converged") else "NO",
                 ("%.4f" % t1) if t1 is not None else "-",
                 ("%.4f" % lw) if lw is not None else "-",
                 r.get("n_dets_90pct", "-"), t))

    print()
    print("=" * 106)
    print("READING")
    print("=" * 106)
    print("  T1 > 0.02        single-reference methods are unreliable; UCCSD and HEA are")
    print("                   built on a single reference, so this is the danger signal.")
    print("  leading wt << 1  the CASCI state is a genuine superposition, so a shallow")
    print("                   ansatz has to represent many determinants at once.")
    tm = [r for r in rows if r.get("status") == "ok" and r["system"] not in ("N2", "H2O")]
    ctl = [r for r in rows if r.get("status") == "ok" and r["system"] in ("N2", "H2O")]
    if tm and ctl:
        tm_t1 = [r["t1_diagnostic"] for r in tm if r.get("t1_diagnostic") is not None]
        ct_t1 = [r["t1_diagnostic"] for r in ctl if r.get("t1_diagnostic") is not None]
        if tm_t1 and ct_t1:
            print()
            print("  transition metals : T1 median %.4f   (max %.4f)"
                  % (float(np.median(tm_t1)), max(tm_t1)))
            print("  suite controls    : T1 median %.4f   (max %.4f)"
                  % (float(np.median(ct_t1)), max(ct_t1)))
            if float(np.median(tm_t1)) > 2 * float(np.median(ct_t1)):
                print()
                print("  The transition-metal systems are markedly more multireference than")
                print("  anything currently in the suite. Entries would very likely land in")
                print("  research tier rather than certified.")


if __name__ == "__main__":
    main()
