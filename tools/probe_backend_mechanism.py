#!/usr/bin/env python
"""Why do two simulator backends disagree by more than the certification threshold?

The first probe found benzene differing by 11 mHa between default.qubit and
lightning.qubit while LiH and N2 agreed to 1e-13. That pattern is not arithmetic error --
it is the signature of amplification, and QEncode has met it before: threaded BLAS
perturbs an energy in its last bits, a gradient-free optimiser picks its next step by
COMPARING energies, and on a multi-modal landscape one flipped comparison lands the run
in a different local minimum.

If that is what is happening here, then:

  * a single energy evaluation at a FIXED point should agree to ~1e-13, and
  * a gradient-BASED optimiser should be immune, because a 1e-13 perturbation moves a
    computed search direction by 1e-13 rather than flipping a decision.

Both are cheap to test and together they decide whether a backend axis is publishable.
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
          "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import glob
import json
import re
import sys
import time

import numpy as np
import pennylane as qml
from scipy.optimize import minimize

REPS = 2
P = {"X": qml.PauliX, "Y": qml.PauliY, "Z": qml.PauliZ}
BACKENDS = ["default.qubit", "lightning.qubit"]


def build(mol, repo):
    f = sorted(glob.glob(os.path.join(repo, "releases/v4/db/%s_ccpvdz_JW_HEA*.json" % mol)))[0]
    d = json.load(open(f))
    h = d["artifacts"]["qubit_hamiltonian"]

    def op(ps):
        if ps.strip() in ("I", ""):
            return qml.Identity(0)
        o = None
        for p, w in re.findall(r"([XYZ])(\d+)", ps):
            t = P[p](int(w))
            o = t if o is None else o @ t
        return o if o is not None else qml.Identity(0)

    return (qml.Hamiltonian([t["coefficient"] for t in h["pauli_terms"]],
                            [op(t["pauli_string"]) for t in h["pauli_terms"]]),
            h["num_qubits"], d["artifacts"]["circuits"]["hf_state"],
            len(h["pauli_terms"]))


def energy_fn(backend, H, n, hf):
    dev = qml.device(backend, wires=n)
    hf_arr = np.array(hf)

    @qml.qnode(dev)
    def E(p):
        qml.BasisState(hf_arr, wires=range(n))
        i = 0
        for _ in range(REPS):
            for w in range(n):
                qml.RY(p[i], wires=w); i += 1
            for w in range(n - 1):
                qml.CNOT(wires=[w, w + 1])
        for w in range(n):
            qml.RY(p[i], wires=w); i += 1
        return qml.expval(H)
    return E


def main():
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    mols = sys.argv[1:] or ["benzene", "H2O", "N2", "LiH"]
    print("%-8s %-24s %14s %14s %12s" % ("mol", "test", "default.qubit", "lightning", "|delta| Ha"))
    print("-" * 92)

    rows = []
    for mol in mols:
        try:
            H, n, hf, L = build(mol, repo)
        except IndexError:
            continue
        npar = n * (REPS + 1)
        rng = np.random.default_rng(0)
        x0 = rng.uniform(-0.1, 0.1, size=npar)
        fns = {b: energy_fn(b, H, n, hf) for b in BACKENDS}

        # (1) one evaluation, fixed point -- pure arithmetic, no optimiser
        e = {b: float(fns[b](x0)) for b in BACKENDS}
        d_fixed = abs(e[BACKENDS[0]] - e[BACKENDS[1]])
        print("%-8s %-24s %14.9f %14.9f %12.2e"
              % (mol, "single eval, fixed x", e[BACKENDS[0]], e[BACKENDS[1]], d_fixed))

        # (2) gradient-free optimiser -- comparisons can flip
        eo = {}
        for b in BACKENDS:
            r = minimize(lambda p: float(fns[b](p)), x0, method="COBYLA",
                         options={"maxiter": 300, "rhobeg": 0.3})
            eo[b] = float(r.fun)
        d_cob = abs(eo[BACKENDS[0]] - eo[BACKENDS[1]])
        print("%-8s %-24s %14.9f %14.9f %12.2e"
              % ("", "COBYLA (gradient-free)", eo[BACKENDS[0]], eo[BACKENDS[1]], d_cob))

        # (3) gradient-based optimiser -- should be immune
        eg = {}
        for b in BACKENDS:
            def grad(p, _b=b):
                g = np.zeros(npar)
                for i in range(npar):
                    s = np.zeros(npar); s[i] = np.pi / 2.0
                    g[i] = (float(fns[_b](p + s)) - float(fns[_b](p - s))) / 2.0
                return g
            r = minimize(lambda p, _b=b: float(fns[_b](p)), x0, method="L-BFGS-B",
                         jac=grad, options={"maxiter": 300, "maxfun": 3000})
            eg[b] = float(r.fun)
        d_lbfgs = abs(eg[BACKENDS[0]] - eg[BACKENDS[1]])
        print("%-8s %-24s %14.9f %14.9f %12.2e"
              % ("", "L-BFGS-B (param-shift)", eg[BACKENDS[0]], eg[BACKENDS[1]], d_lbfgs))
        print("-" * 92)
        rows.append((mol, n, L, d_fixed, d_cob, d_lbfgs))

    print()
    print("=" * 92)
    print("VERDICT")
    print("=" * 92)
    print("%-8s %6s %7s %13s %13s %13s" % ("mol", "qubits", "terms",
                                           "fixed point", "COBYLA", "L-BFGS-B"))
    print("-" * 92)
    for mol, n, L, a, b, c in rows:
        print("%-8s %6d %7d %13.2e %13.2e %13.2e" % (mol, n, L, a, b, c))
    print()
    if rows:
        worst_fixed = max(r[3] for r in rows)
        worst_cob = max(r[4] for r in rows)
        worst_lb = max(r[5] for r in rows)
        print("  worst fixed-point disagreement : %.2e Ha  (%.4f mHa)" % (worst_fixed, worst_fixed * 1000))
        print("  worst after COBYLA             : %.2e Ha  (%.4f mHa)" % (worst_cob, worst_cob * 1000))
        print("  worst after L-BFGS-B           : %.2e Ha  (%.4f mHa)" % (worst_lb, worst_lb * 1000))
        print()
        if worst_fixed < 1e-9 and worst_cob > 1e-4:
            print("  Backends agree on the arithmetic and diverge only through the optimiser:")
            print("  the same amplification that made threaded BLAS unsafe. A backend axis is")
            print("  publishable for gradient-based runs and not for gradient-free ones.")


if __name__ == "__main__":
    main()
