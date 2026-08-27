#!/usr/bin/env python
"""Does the binomial sampling model equal real PennyLane circuit sampling?

neyman_validate.py draws each Pauli term from Binomial(s, (1+<P>)/2) instead of running
the circuit s times. That is claimed to be the exact same distribution, since a Pauli
observable has +-1 eigenvalues. A claim like that has to be tested, not asserted --
the whole point of redoing this work is that I stopped asserting things.

Runs both paths on the same state and allocation and compares the estimator spread.
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
          "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import json, glob, re, sys
import numpy as np
import pennylane as qml

REPS = 2
P = {"X": qml.PauliX, "Y": qml.PauliY, "Z": qml.PauliZ}
REPEATS = 200
SHOTS = 500


def build(mol, repo):
    d = json.load(open(sorted(glob.glob(os.path.join(
        repo, "releases/v4/db/%s_ccpvdz_JW_HEA*.json" % mol)))[0]))
    h = d["artifacts"]["qubit_hamiltonian"]

    def op(ps):
        if ps.strip() in ("I", ""):
            return None
        o = None
        for p, w in re.findall(r"([XYZ])(\d+)", ps):
            t = P[p](int(w))
            o = t if o is None else o @ t
        return o
    return (np.array([t["coefficient"] for t in h["pauli_terms"]], dtype=float),
            [op(t["pauli_string"]) for t in h["pauli_terms"]],
            h["num_qubits"], d["artifacts"]["circuits"]["hf_state"])


def main():
    mol = sys.argv[1] if len(sys.argv) > 1 else "H2O"
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    coeffs, obs, n, hf = build(mol, repo)
    L = len(coeffs)
    hf_arr = np.array(hf)
    params = np.random.default_rng(0).uniform(-0.1, 0.1, size=n * (REPS + 1))

    def body():
        qml.BasisState(hf_arr, wires=range(n))
        i = 0
        for _ in range(REPS):
            for w in range(n):
                qml.RY(params[i], wires=w); i += 1
            for w in range(n - 1):
                qml.CNOT(wires=[w, w + 1])
        for w in range(n):
            qml.RY(params[i], wires=w); i += 1

    devx = qml.device("default.qubit", wires=n)
    Hops = [o if o is not None else qml.Identity(0) for o in obs]

    @qml.qnode(devx)
    def exp_all():
        body()
        return [qml.expval(o) for o in Hops]

    means = np.array([float(x) for x in exp_all()])
    live = np.array([o is not None for o in obs])
    ident = float(coeffs[~live].sum()) if (~live).any() else 0.0

    # --- path A: real circuit sampling, one device per term ------------------
    rngA = np.random.default_rng(3)
    valsA = np.empty(REPEATS)
    for r in range(REPEATS):
        tot = ident
        for i in range(L):
            if not live[i]:
                continue
            dev = qml.device("default.qubit", wires=n, shots=SHOTS,
                             seed=int(rngA.integers(1 << 30)))

            @qml.qnode(dev)
            def f():
                body()
                return qml.expval(obs[i])
            tot += coeffs[i] * float(f())
        valsA[r] = tot

    # --- path B: binomial model ---------------------------------------------
    rngB = np.random.default_rng(4)
    idx = np.nonzero(live)[0]
    p1 = np.clip((1.0 + means[idx]) / 2.0, 0.0, 1.0)
    valsB = np.empty(REPEATS)
    for r in range(REPEATS):
        k = rngB.binomial(SHOTS, p1)
        valsB[r] = ident + float(np.dot(coeffs[idx], (2.0 * k - SHOTS) / SHOTS))

    sA, sB = valsA.std(ddof=1) * 1000, valsB.std(ddof=1) * 1000
    # F-test style interval on the ratio of two sample stds (n=REPEATS)
    se = np.sqrt(2.0 / (REPEATS - 1))
    print("%s  L=%d  shots/term=%d  repeats=%d" % (mol, L, SHOTS, REPEATS))
    print("  circuit sampling : std = %8.4f mHa   mean err = %8.4f" % (sA, valsA.mean() * 1000 - float(np.dot(coeffs, means)) * 1000))
    print("  binomial model   : std = %8.4f mHa   mean err = %8.4f" % (sB, valsB.mean() * 1000 - float(np.dot(coeffs, means)) * 1000))
    print("  ratio A/B = %.4f   (1 +- %.3f expected from sampling noise alone)"
          % (sA / sB, 1.96 * se))
    ok = abs(np.log(sA / sB)) < 1.96 * se
    print("  VERDICT:", "consistent -- binomial model is valid" if ok
          else "INCONSISTENT -- do not use the binomial shortcut")


if __name__ == "__main__":
    main()
