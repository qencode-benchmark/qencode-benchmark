#!/usr/bin/env python
"""What would a published QEncode entry look like on noisy hardware?

Every certified entry is an exact statevector result. That is the right way to measure an
algorithm, and it is not what a device would return. This takes each published
hardware-efficient entry, rebuilds its circuit from the optimal parameters it recorded,
and re-evaluates the same energy under named gate-noise models.

Two things make this different from the shot-noise work:

  * shot noise is zero mean -- more shots shrink it, and the estimator is unbiased.
    Gate noise is a BIAS. Every channel here is dissipative and drives the state toward
    the maximally mixed state, whose energy is the mean of the spectrum. Averaging does
    not remove it, and it can only push the energy up.
  * density-matrix simulation costs 4^n rather than 2^n, so there is a hard size ceiling.
    This measures where it is rather than assuming.

A hard gate runs first: the rebuilt noiseless circuit must reproduce the energy stored in
the entry. If it does not, the reconstruction is wrong and every noisy number below it
would be meaningless, so the molecule is reported as a failure rather than a result.

Restricted to hardware-efficient entries, whose circuit is fully determined by
(qubits, layers, parameters). UCCSD and ADAPT circuits are not reconstructable from the
stored fields alone.

    python probe_gate_noise.py [molecule ...]
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noise_models  # noqa: E402

P = {"X": qml.PauliX, "Y": qml.PauliY, "Z": qml.PauliZ}
REBUILD_TOL = 1e-6          # Ha; the rebuild must match the published energy this closely
QUBIT_CEILING = 10          # 4^n density matrix; above this a single point takes minutes


def load(path):
    d = json.load(open(path))
    h = d["artifacts"]["qubit_hamiltonian"]

    def op(ps):
        if ps.strip() in ("I", ""):
            return qml.Identity(0)
        o = None
        for p, w in re.findall(r"([XYZ])(\d+)", ps):
            t = P[p](int(w))
            o = t if o is None else o @ t
        return o if o is not None else qml.Identity(0)

    vqe = d["results"]["vqe"]
    cs = d.get("circuit_stats", {})
    n = h["num_qubits"]
    params = np.array(vqe["optimal_params"], dtype=float)
    npar = len(params)
    if n <= 0 or npar % n:
        return None
    reps = npar // n - 1
    if reps < 1:
        return None
    return {
        "entry_id": d["entry_id"],
        "molecule": (d.get("problem") or {}).get("molecule") or (d.get("problem") or {}).get("name") or "?",
        "H": qml.Hamiltonian([t["coefficient"] for t in h["pauli_terms"]],
                             [op(t["pauli_string"]) for t in h["pauli_terms"]]),
        "n": n, "reps": reps, "params": params,
        "hf": np.array(d["artifacts"]["circuits"]["hf_state"]),
        "e_published": float(vqe["best_energy_hartree"]),
        "e_exact": float(d["results"]["reference"]["exact_qubit_ground_energy_hartree"]),
        "n_2q": cs.get("ansatz_num_2q_gates"),
        "n_1q": cs.get("ansatz_num_1q_gates"),
        "depth": cs.get("ansatz_depth"),
    }


def energy(rec, device, after_1q, after_2q):
    n, reps, hf = rec["n"], rec["reps"], rec["hf"]
    dev = qml.device(device, wires=n)

    @qml.qnode(dev)
    def E(p):
        qml.BasisState(hf, wires=range(n))
        i = 0
        for _ in range(reps):
            for w in range(n):
                qml.RY(p[i], wires=w); i += 1
                after_1q(w)
            for w in range(n - 1):
                qml.CNOT(wires=[w, w + 1])
                after_2q([w, w + 1])
        for w in range(n):
            qml.RY(p[i], wires=w); i += 1
            after_1q(w)
        return qml.expval(rec["H"])
    return float(E(rec["params"]))


def main():
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    want = set(sys.argv[1:])
    files = sorted(glob.glob(os.path.join(repo, "releases/v4/db/*_HEA_*.json")))

    recs = []
    for f in files:
        r = load(f)
        if r is None:
            continue
        mol = os.path.basename(f).split("_")[0]
        r["mol"] = mol
        if want and mol not in want:
            continue
        recs.append(r)
    # one entry per molecule, the smallest, to keep the density matrices affordable
    best = {}
    for r in recs:
        if r["mol"] not in best or r["n"] < best[r["mol"]]["n"]:
            best[r["mol"]] = r
    recs = sorted(best.values(), key=lambda r: r["n"])

    print("noise models:", ", ".join(noise_models.names()))
    print()
    print("=" * 118)
    print("STEP 1 -- can the published circuit be rebuilt from what the entry records?")
    print("=" * 118)
    print("%-12s %6s %5s %6s %18s %18s %12s %s"
          % ("molecule", "qubits", "reps", "2Q", "published (Ha)", "rebuilt (Ha)", "|diff|", "gate"))
    print("-" * 118)
    ok = []
    ideal_dev, i1, i2, _ = noise_models.get("ideal/v1")
    for r in recs:
        t0 = time.time()
        try:
            e = energy(r, ideal_dev, i1, i2)
        except Exception as exc:
            print("%-12s  rebuild failed: %s" % (r["mol"], str(exc)[:60]))
            continue
        d = abs(e - r["e_published"])
        good = d < REBUILD_TOL
        print("%-12s %6d %5d %6s %18.10f %18.10f %12.2e %s"
              % (r["mol"], r["n"], r["reps"], r["n_2q"], r["e_published"], e, d,
                 "OK" if good else "MISMATCH -- excluded"))
        if good:
            r["e_noiseless"] = e
            ok.append(r)
    print()
    if not ok:
        print("  no molecule rebuilt cleanly; nothing below would mean anything.")
        return

    runnable = [r for r in ok if r["n"] <= QUBIT_CEILING]
    skipped = [r for r in ok if r["n"] > QUBIT_CEILING]
    if skipped:
        print("  above the %d-qubit density-matrix ceiling, not run: %s"
              % (QUBIT_CEILING, ", ".join("%s (%dq, dim %d)" % (r["mol"], r["n"], 4 ** r["n"])
                                          for r in skipped)))
        print()

    print("=" * 118)
    print("STEP 2 -- the same published result, re-evaluated under gate noise")
    print("  dE is the energy SHIFT caused by noise. Positive means noise pushed the")
    print("  energy up, which is what a dissipative channel must do.")
    print("=" * 118)
    models = [m for m in noise_models.names() if m != "ideal/v1"]
    print("%-12s %6s %6s %14s %s" % ("molecule", "qubits", "2Q", "noiseless gap",
                                     "  ".join("%22s" % m.replace("/v1", "") for m in models)))
    print("-" * 118)
    rows = []
    for r in runnable:
        cells = []
        for m in models:
            dev, a1, a2, _ = noise_models.get(m)
            t0 = time.time()
            try:
                e = energy(r, dev, a1, a2)
                d = (e - r["e_noiseless"]) * 1000.0
                cells.append("%16.2f mHa" % d)
                rows.append({"mol": r["mol"], "n": r["n"], "n_2q": r["n_2q"],
                             "model": m, "dE_mha": d,
                             "p2": noise_models.NOISE_MODELS[m]["params"].get("p_2q", 0.0),
                             "secs": round(time.time() - t0, 1)})
            except Exception as exc:
                cells.append("%22s" % ("err " + str(exc)[:14]))
        gap = abs(r["e_noiseless"] - r["e_exact"]) * 1000.0
        print("%-12s %6d %6s %11.3f mHa %s"
              % (r["mol"], r["n"], r["n_2q"], gap, "  ".join(cells)))

    if not rows:
        return
    print()
    print("=" * 118)
    print("STEP 3 -- is the bias predictable from circuit structure?")
    print("  If it is, the noisy energy can be estimated from the noiseless one plus a")
    print("  gate count, and the 4^n simulation is only needed to calibrate the constant.")
    print("=" * 118)
    print("%-12s %6s %8s %12s %14s %12s"
          % ("molecule", "2Q", "p_2q", "dE (mHa)", "dE/(p2*N2Q)", "seconds"))
    print("-" * 118)
    ratios = []
    for row in sorted(rows, key=lambda x: (x["model"], x["n"])):
        denom = row["p2"] * (row["n_2q"] or 0)
        rr = row["dE_mha"] / denom if denom > 0 else float("nan")
        if np.isfinite(rr):
            ratios.append(rr)
        print("%-12s %6s %8.1e %12.3f %14.1f %11.1fs"
              % (row["mol"] + " " + row["model"].replace("/v1", "").replace("depolarizing-", "d-"),
                 row["n_2q"], row["p2"], row["dE_mha"], rr, row["secs"]))
    if ratios:
        a = np.array(ratios)
        print()
        print("  dE / (p_2q * N_2Q):  median %.1f   spread %.1f to %.1f   (mHa per unit)"
              % (np.median(a), a.min(), a.max()))
        spread = a.max() / max(a.min(), 1e-12)
        if spread < 3:
            print("  Within a factor of %.1f across molecules and rates, so the bias is" % spread)
            print("  largely set by p_2q * N_2Q and can be estimated without a 4^n simulation.")
        else:
            print("  Spread of %.1fx is too wide for a one-parameter rule: the bias depends" % spread)
            print("  on more than the two-qubit gate count -- most likely on how far the")
            print("  state is from the maximally mixed state, which differs per molecule.")


if __name__ == "__main__":
    main()
