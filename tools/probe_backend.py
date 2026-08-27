#!/usr/bin/env python
"""Feasibility probe: is a second simulator backend reproducible against the first?

QEncode's guarantee is that an entry can be rebuilt digit for digit. That guarantee is
currently established for one backend. Adding a second is not a free extension -- it is a
second determinism story that has to be validated, and if the two backends disagree in
the last bits then a "backend" column on the leaderboard would be comparing things that
are not comparable.

This measures three things, none of which change the suite:

  1. within-backend determinism -- same backend, same seed, repeated. Must be exact.
  2. cross-backend agreement    -- default.qubit vs lightning.qubit on identical input.
  3. speed                      -- what the second backend would actually buy.

Nothing is written to the entry database.

    python probe_backend.py [molecule ...]
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

    coeffs = [t["coefficient"] for t in h["pauli_terms"]]
    obs = [op(t["pauli_string"]) for t in h["pauli_terms"]]
    return (qml.Hamiltonian(coeffs, obs), h["num_qubits"],
            d["artifacts"]["circuits"]["hf_state"], len(coeffs))


def run(backend, H, n, hf, seed, maxiter):
    """One full COBYLA optimisation on the named backend."""
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

    x0 = np.random.default_rng(seed).uniform(-0.1, 0.1, size=n * (REPS + 1))
    t0 = time.time()
    r = minimize(lambda p: float(E(p)), x0, method="COBYLA",
                 options={"maxiter": maxiter, "rhobeg": 0.3})
    return float(r.fun), round(time.time() - t0, 2), int(r.nfev)


def main():
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    mols = sys.argv[1:] or ["H2O", "LiH", "N2"]
    print("pennylane %s   backends: %s" % (qml.__version__, ", ".join(BACKENDS)))
    print()

    verdicts = []
    for mol in mols:
        try:
            H, n, hf, L = build(mol, repo)
        except IndexError:
            print("%-6s no JW/HEA entry, skipping" % mol)
            continue
        print("=" * 96)
        print("%s   %d qubits, %d Pauli terms" % (mol, n, L))
        print("=" * 96)

        results = {}
        for b in BACKENDS:
            # (1) within-backend determinism: identical inputs, run twice
            e1, t1, nf1 = run(b, H, n, hf, seed=0, maxiter=200)
            e2, t2, _ = run(b, H, n, hf, seed=0, maxiter=200)
            same = (e1 == e2)
            results[b] = (e1, (t1 + t2) / 2.0, nf1, same)
            print("  %-16s E = %.15f   %6.2f s   %4d evals   repeat-identical: %s"
                  % (b, e1, (t1 + t2) / 2.0, nf1, "YES" if same else "NO"))

        # (2) cross-backend agreement
        a, bb = BACKENDS[0], BACKENDS[1]
        ea, eb = results[a][0], results[bb][0]
        diff = abs(ea - eb)
        exact = (ea == eb)
        speed = results[a][1] / max(results[bb][1], 1e-9)
        print("  %-16s |Δ| = %.3e Ha  (%.3e mHa)   bit-identical: %s"
              % ("cross-backend", diff, diff * 1000, "YES" if exact else "NO"))
        print("  %-16s %.2fx  (>1 means %s is faster)" % ("speed", speed, bb))
        verdicts.append((mol, n, L, results[a][3] and results[bb][3], exact, diff, speed))
        print()

    print("=" * 96)
    print("SUMMARY")
    print("=" * 96)
    print("%-6s %6s %7s %14s %14s %14s %8s"
          % ("mol", "qubits", "terms", "each repeats", "backends agree", "|Δ| Ha", "speedup"))
    print("-" * 96)
    for mol, n, L, rep, exact, diff, speed in verdicts:
        print("%-6s %6d %7d %14s %14s %14.2e %7.2fx"
              % (mol, n, L, "YES" if rep else "NO", "bit-exact" if exact else "no", diff, speed))
    print()
    if verdicts and all(v[3] for v in verdicts):
        print("  Each backend is internally deterministic.")
    else:
        print("  WARNING: a backend did not reproduce itself. That is disqualifying.")
    if verdicts and all(v[4] for v in verdicts):
        print("  The two backends agree bit for bit: a backend column would be comparable.")
    else:
        worst = max(v[5] for v in verdicts) if verdicts else 0.0
        print("  The two backends do NOT agree bit for bit; worst |Δ| = %.2e Ha (%.3f mHa)."
              % (worst, worst * 1000))
        print("  Entries from different backends would not be directly comparable at the")
        print("  digits QEncode certifies on, so a backend axis needs its own tolerance")
        print("  policy before it can be published.")


if __name__ == "__main__":
    main()
