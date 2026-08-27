#!/usr/bin/env python
"""Validate Neyman shot allocation before anything is published.

The preliminary result rested on ONE parameter point and TWO molecules. Term variances
depend on the quantum state, so an advantage seen at a random start need not survive
near convergence -- which is where an optimiser actually spends its time.

Design:
  * 10 molecules, 20 to 919 Pauli terms
  * 3 states: random start / mid-optimisation / converged  (all found EXACTLY, no shots)
  * 3 total shot budgets
  * 40 repeats per scheme

Schemes, all charged the SAME total budget, shots counted PER TERM so the total is
exactly sum(alloc) -- no commuting-group accounting to get wrong this time:
  uniform  : s_i = N / L
  weighted : s_i ~ |c_i|                 (Rosalin weighted random sampling)
  neyman   : s_i ~ |c_i| * sigma_hat_i   (variance-aware; pilot paid out of the budget)
  oracle   : s_i ~ |c_i| * sigma_i       (exact sigma, no pilot -- the method ceiling)

Crucially this also records the ANALYTIC prediction. For independent per-term estimators
with s_i shots each, Var(E) = sum_i c_i^2 sigma_i^2 / s_i, giving closed forms:

  uniform   Var = (L / N)   * sum c_i^2 sigma_i^2
  weighted  Var = (1 / N)   * (sum|c_i|) * (sum |c_i| sigma_i^2)
  neyman    Var = (1 / N)   * (sum |c_i| sigma_i)^2      <- the minimum, by Cauchy-Schwarz

If the measured ratios track these, the effect is understood rather than merely observed,
and the gain for a new molecule can be predicted without running anything.

    python neyman_validate.py <molecule> <state> <budget> <outdir>
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
          "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import json, glob, re, sys, time, traceback
import numpy as np
import pennylane as qml
from scipy.optimize import minimize

REPS = 2
REPEATS = 40
PILOT_FRAC = 0.10
P = {"X": qml.PauliX, "Y": qml.PauliY, "Z": qml.PauliZ}


def build(mol, repo):
    f = sorted(glob.glob(os.path.join(
        repo, "releases/v4/db/%s_ccpvdz_JW_HEA*.json" % mol)))[0]
    d = json.load(open(f))
    h = d["artifacts"]["qubit_hamiltonian"]

    def op(ps):
        if ps.strip() in ("I", ""):
            return None
        o = None
        for p, w in re.findall(r"([XYZ])(\d+)", ps):
            t = P[p](int(w))
            o = t if o is None else o @ t
        return o

    coeffs = np.array([t["coefficient"] for t in h["pauli_terms"]], dtype=float)
    obs = [op(t["pauli_string"]) for t in h["pauli_terms"]]
    return (coeffs, obs, h["num_qubits"],
            d["artifacts"]["circuits"]["hf_state"], os.path.basename(f))


def ansatz_factory(n, hf):
    hf_arr = np.array(hf)

    def body(params):
        qml.BasisState(hf_arr, wires=range(n))
        i = 0
        for _ in range(REPS):
            for w in range(n):
                qml.RY(params[i], wires=w); i += 1
            for w in range(n - 1):
                qml.CNOT(wires=[w, w + 1])
        for w in range(n):
            qml.RY(params[i], wires=w); i += 1
    return body


def main():
    mol, state, budget_s, outdir = sys.argv[1:5]
    budget = int(budget_s)
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    tag = "%s_%s_b%d" % (mol, state, budget)
    rec = {"molecule": mol, "state": state, "budget": budget, "tag": tag,
           "repeats": REPEATS, "pilot_frac": PILOT_FRAC, "reps": REPS,
           "pennylane": qml.__version__}
    t0 = time.time()
    try:
        coeffs, obs, n, hf, src = build(mol, repo)
        L = len(coeffs)
        rec["source_entry"] = src
        npar = n * (REPS + 1)
        body = ansatz_factory(n, hf)
        devx = qml.device("default.qubit", wires=n)
        Hops = [o if o is not None else qml.Identity(0) for o in obs]
        H = qml.Hamiltonian(list(coeffs), Hops)

        @qml.qnode(devx)
        def Ex(p):
            body(p)
            return qml.expval(H)

        # ---- the state to measure at ---------------------------------------
        x0 = np.random.default_rng(0).uniform(-0.1, 0.1, size=npar)
        if state == "start":
            params = x0
            nfev = 0
        else:
            mx = 40 if state == "mid" else 3000
            r = minimize(lambda p: float(Ex(p)), x0, method="COBYLA",
                         options={"maxiter": mx, "rhobeg": 0.3})
            params = np.array(r.x)
            nfev = int(r.nfev)
        rec["opt_nfev"] = nfev
        e_true = float(Ex(params))

        # ---- EXACT per-term sigma, by statevector (no sampling) ------------
        @qml.qnode(devx)
        def exp_all(p):
            body(p)
            return [qml.expval(o) for o in Hops]

        means = np.array([float(x) for x in exp_all(params)])
        live = np.array([o is not None for o in obs])
        sigma = np.where(live, np.sqrt(np.clip(1.0 - means ** 2, 0.0, None)), 0.0)
        nlive = int(live.sum())

        # ---- analytic variances at this budget -----------------------------
        a = np.abs(coeffs)
        cs2 = (coeffs ** 2) * (sigma ** 2)
        var_uni = nlive * cs2.sum() / budget
        var_wgt = (a * live).sum() * ((a * sigma ** 2) * live).sum() / budget
        var_ney = ((a * sigma).sum()) ** 2 / budget
        rec["analytic"] = {
            "std_uniform_mha": float(np.sqrt(max(var_uni, 0.0)) * 1000),
            "std_weighted_mha": float(np.sqrt(max(var_wgt, 0.0)) * 1000),
            "std_neyman_mha": float(np.sqrt(max(var_ney, 0.0)) * 1000),
            "pred_neyman_vs_uniform": float(np.sqrt(var_uni / max(var_ney, 1e-300))),
            "pred_neyman_vs_weighted": float(np.sqrt(var_wgt / max(var_ney, 1e-300))),
        }

        # ---- pilot estimate of sigma, charged to the budget ----------------
        pilot = int(budget * PILOT_FRAC)
        per = max(2, pilot // max(nlive, 1))
        rng_p = np.random.default_rng(999)
        sig_hat = np.zeros(L)
        for i in range(L):
            if not live[i]:
                continue
            p1 = min(max((1.0 + means[i]) / 2.0, 0.0), 1.0)
            k = rng_p.binomial(per, p1)
            m = (2.0 * k - per) / float(per)
            sig_hat[i] = np.sqrt(max(0.0, 1.0 - m * m))

        allocs = {}
        allocs["uniform"] = np.where(live, budget // max(nlive, 1), 0).astype(np.int64)
        w = a * live
        allocs["weighted"] = np.floor(w / max(w.sum(), 1e-300) * budget).astype(np.int64)
        nh = a * sig_hat
        allocs["neyman"] = np.floor(nh / max(nh.sum(), 1e-300) * (budget - pilot)).astype(np.int64)
        no = a * sigma
        allocs["oracle"] = np.floor(no / max(no.sum(), 1e-300) * budget).astype(np.int64)

        # ---- measure -------------------------------------------------------
        # A Pauli term has +-1 eigenvalues, so s shots is a Binomial draw with
        # p = (1+<P>)/2 and estimator (2k-s)/s. That is EXACTLY the distribution the
        # circuit produces, so 40 repeats across 919 terms stays affordable and the
        # statistics are identical to running the circuit.
        out = {}
        ident = float(coeffs[~live].sum()) if (~live).any() else 0.0
        for name, al in allocs.items():
            rng = np.random.default_rng(11)
            idx = np.nonzero(al > 0)[0]
            s = al[idx].astype(np.int64)
            p1 = np.clip((1.0 + means[idx]) / 2.0, 0.0, 1.0)
            c_idx = coeffs[idx]
            vals = np.empty(REPEATS)
            for r_i in range(REPEATS):
                k = rng.binomial(s, p1)
                est = (2.0 * k - s) / s
                vals[r_i] = ident + float(np.dot(c_idx, est))
            cost = int(al.sum()) + (pilot if name == "neyman" else 0)
            out[name] = {
                "std_mha": float(vals.std(ddof=1) * 1000),
                "mean_err_mha": float((vals.mean() - e_true) * 1000),
                "shots": cost,
                "terms_funded": int((al > 0).sum()),
            }

        rec.update({
            "n_terms": L, "n_qubits": n, "n_live_terms": nlive,
            "lambda": float(a.sum()),
            "zero_variance_terms": int(((sigma < 1e-9) & live).sum()),
            "exact_energy": e_true,
            "schemes": out,
            "neyman_vs_uniform": out["uniform"]["std_mha"] / max(out["neyman"]["std_mha"], 1e-300),
            "neyman_vs_weighted": out["weighted"]["std_mha"] / max(out["neyman"]["std_mha"], 1e-300),
            "neyman_vs_oracle": out["neyman"]["std_mha"] / max(out["oracle"]["std_mha"], 1e-300),
            "runtime_s": round(time.time() - t0, 1),
            "status": "ok",
        })
    except Exception:
        rec.update({"status": "error", "traceback": traceback.format_exc()[-900:],
                    "runtime_s": round(time.time() - t0, 1)})

    os.makedirs(outdir, exist_ok=True)
    json.dump(rec, open(os.path.join(outdir, tag + ".json"), "w"), indent=1)
    if rec["status"] == "ok":
        s = rec["schemes"]
        print("%-22s L=%-4d uni=%9.3f wgt=%9.3f ney=%9.3f | meas %6.2fx  theory %6.2fx"
              % (tag, rec["n_terms"], s["uniform"]["std_mha"], s["weighted"]["std_mha"],
                 s["neyman"]["std_mha"], rec["neyman_vs_uniform"],
                 rec["analytic"]["pred_neyman_vs_uniform"]))
    else:
        print("%-22s ERROR %s" % (tag, rec["traceback"].strip().splitlines()[-1][:80]))


if __name__ == "__main__":
    main()
