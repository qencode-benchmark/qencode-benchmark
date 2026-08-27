#!/usr/bin/env python
"""Neyman shot allocation, v2: diagnose the failure and test the fixes.

v1 found that Neyman allocation with a pilot-estimated sigma is CATASTROPHICALLY biased
-- up to 3200 mHa, a thousand times worse than plain uniform allocation -- even though
its variance is the lowest of any scheme. The oracle version (exact sigma) is unbiased
and does beat uniform, so the allocation rule is fine; the estimator of sigma is not.

Mechanism: with `per` pilot shots, sigma_hat = sqrt(1 - m^2) is EXACTLY zero whenever
the pilot draw is all-heads or all-tails. For a near-deterministic term (|<P>| close to
1) that is likely. Such a term is then allocated zero shots and silently dropped from
the energy sum. Near-deterministic Pauli strings tend to carry LARGE coefficients, so
the rule preferentially discards the terms that matter most.

Schemes tested here (all charged the same total budget):
  uniform     s_i = N/L
  weighted    s_i ~ |c_i|
  oracle      s_i ~ |c_i| sigma_i          exact sigma, no pilot -- the ceiling
  naive       s_i ~ |c_i| sigma_hat_i      v1 behaviour, for the record
  retain      naive, but a starved term contributes its PILOT estimate instead of zero
  shrunk      sigma_hat from Agresti-Coull p = (k+1)/(per+2), which is never exactly 0
  fixed       shrunk + retain + a floor of 1 shot per live term
  pooled      naive allocation, but pilot and main samples pooled for every term
  best        shrunk allocation + floor + pooling -- nothing starved, nothing discarded
"""
import os
for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
          "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[v] = "1"
import json, glob, re, sys, time, traceback
import numpy as np
import pennylane as qml
from scipy.optimize import minimize

def _provenance():
    """Same shape as a certified suite entry, so an experiment record can be audited
    the same way. Versions come from package metadata, not imports -- importing pyscf
    to read its version would cost more than the measurement."""
    import platform
    import subprocess
    from importlib.metadata import version, PackageNotFoundError

    def _v(pkg):
        try:
            return version(pkg)
        except PackageNotFoundError:
            return None

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.environ.get("QENCODE_REPO", os.getcwd()),
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        commit = None

    return {
        "tool_versions": {
            "python": platform.python_version(),
            "pyscf": _v("pyscf"),
            "pennylane": _v("pennylane"),
            "openfermion": _v("openfermion"),
            "numpy": _v("numpy"),
            "scipy": _v("scipy"),
            "git_commit": commit,
        },
        "environment": {
            "platform": sys.platform,
            "blas_threads": os.environ.get("OMP_NUM_THREADS"),
            "threads_pinned": os.environ.get("OMP_NUM_THREADS") == "1",
        },
    }


REPS = 2
REPEATS = 200
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
    return (np.array([t["coefficient"] for t in h["pauli_terms"]], dtype=float),
            [op(t["pauli_string"]) for t in h["pauli_terms"]],
            h["num_qubits"], d["artifacts"]["circuits"]["hf_state"], os.path.basename(f))


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


def alloc_from(weights, live, total):
    w = np.where(live, weights, 0.0)
    s = w.sum()
    if s <= 0:
        return np.where(live, total // max(int(live.sum()), 1), 0).astype(np.int64)
    return np.floor(w / s * total).astype(np.int64)


def alloc_with_floor(weights, live, total):
    """Guarantee every live term at least one shot, then Neyman-split the remainder."""
    nlive = int(live.sum())
    if total <= nlive:
        return np.where(live, 1, 0).astype(np.int64)
    base = np.where(live, 1, 0).astype(np.int64)
    return base + alloc_from(weights, live, total - nlive)


def main():
    mol, state, budget_s, outdir = sys.argv[1:5]
    budget = int(budget_s)
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    tag = "%s_%s_b%d" % (mol, state, budget)
    rec = {"molecule": mol, "state": state, "budget": budget, "tag": tag,
           "repeats": REPEATS, "pilot_frac": PILOT_FRAC, "reps": REPS,
           "provenance": _provenance(),
           "pennylane": qml.__version__, "version": 2}
    t0 = time.time()
    try:
        coeffs, obs, n, hf, src = build(mol, repo)
        L = len(coeffs)
        rec["source_entry"] = src
        body = ansatz_factory(n, hf)
        devx = qml.device("default.qubit", wires=n)
        Hops = [o if o is not None else qml.Identity(0) for o in obs]
        H = qml.Hamiltonian(list(coeffs), Hops)

        @qml.qnode(devx)
        def Ex(p):
            body(p)
            return qml.expval(H)

        x0 = np.random.default_rng(0).uniform(-0.1, 0.1, size=n * (REPS + 1))
        if state == "start":
            params, nfev = x0, 0
        else:
            r = minimize(lambda p: float(Ex(p)), x0, method="COBYLA",
                         options={"maxiter": 40 if state == "mid" else 3000, "rhobeg": 0.3})
            params, nfev = np.array(r.x), int(r.nfev)
        rec["opt_nfev"] = nfev
        e_true = float(Ex(params))

        @qml.qnode(devx)
        def exp_all(p):
            body(p)
            return [qml.expval(o) for o in Hops]

        means = np.array([float(x) for x in exp_all(params)])
        live = np.array([o is not None for o in obs])
        sigma = np.where(live, np.sqrt(np.clip(1.0 - means ** 2, 0.0, None)), 0.0)
        nlive = int(live.sum())
        a = np.abs(coeffs)
        ident = float(coeffs[~live].sum()) if (~live).any() else 0.0

        pilot = int(budget * PILOT_FRAC)
        per = max(2, pilot // max(nlive, 1))
        rec["pilot_shots_per_term"] = per

        # ---- pilot draw, shared by every pilot-based scheme -----------------
        rng_p = np.random.default_rng(999)
        idx_live = np.nonzero(live)[0]
        p1_live = np.clip((1.0 + means[idx_live]) / 2.0, 0.0, 1.0)
        k = rng_p.binomial(per, p1_live)
        m_pilot = np.zeros(L)
        m_pilot[idx_live] = (2.0 * k - per) / float(per)
        sig_naive = np.zeros(L)
        sig_naive[idx_live] = np.sqrt(np.clip(1.0 - m_pilot[idx_live] ** 2, 0.0, None))
        # Agresti-Coull: p = (k+1)/(per+2) is never 0 or 1, so sigma is never exactly 0
        p_ac = (k + 1.0) / (per + 2.0)
        sig_shrunk = np.zeros(L)
        sig_shrunk[idx_live] = 2.0 * np.sqrt(p_ac * (1.0 - p_ac))

        # ---- diagnostic: are the terms killed by sig_hat=0 the big ones? ----
        killed = np.zeros(L, dtype=bool)
        killed[idx_live] = (sig_naive[idx_live] <= 0.0)
        rec["diagnostic"] = {
            "n_sigma_hat_zero": int(killed.sum()),
            "mean_abs_c_killed": float(a[killed].mean()) if killed.any() else 0.0,
            "mean_abs_c_kept": float(a[live & ~killed].mean()) if (live & ~killed).any() else 0.0,
            "sum_abs_c_killed": float(a[killed].sum()),
            "lambda": float(a[live].sum()),
            "mean_abs_sigma_killed": float(sigma[killed].mean()) if killed.any() else 0.0,
            "mean_abs_sigma_kept": float(sigma[live & ~killed].mean()) if (live & ~killed).any() else 0.0,
        }

        allocs, retain_from = {}, {}
        allocs["uniform"] = np.where(live, budget // max(nlive, 1), 0).astype(np.int64)
        allocs["weighted"] = alloc_from(a, live, budget)
        allocs["oracle"] = alloc_from(a * sigma, live, budget)
        allocs["naive"] = alloc_from(a * sig_naive, live, budget - pilot)
        allocs["retain"] = allocs["naive"].copy()
        retain_from["retain"] = True
        allocs["shrunk"] = alloc_from(a * sig_shrunk, live, budget - pilot)
        allocs["fixed"] = alloc_with_floor(a * sig_shrunk, live, budget - pilot)
        retain_from["fixed"] = True
        # pooled: allocate as naive, but combine the pilot and main samples for EVERY
        # term rather than only rescuing starved ones. The pilot is already paid for;
        # throwing its information away is pure waste.
        allocs["pooled"] = allocs["naive"].copy()
        # best: shrunk sigma so nothing is ever starved, AND pool pilot with main
        allocs["best"] = alloc_with_floor(a * sig_shrunk, live, budget - pilot)

        out = {}
        for name, al in allocs.items():
            rng = np.random.default_rng(11)
            funded = np.nonzero(al > 0)[0]
            s = al[funded].astype(np.int64)
            pf = np.clip((1.0 + means[funded]) / 2.0, 0.0, 1.0)
            c_f = coeffs[funded]
            # starved live terms: contribute the pilot estimate if the scheme retains it
            starved = np.nonzero(live & (al <= 0))[0]
            base = ident
            if retain_from.get(name) and starved.size:
                base += float(np.dot(coeffs[starved], m_pilot[starved]))
            vals = np.empty(REPEATS)
            if name in ("pooled", "best"):
                # every live term contributes; its mean is the shot-weighted pool of the
                # pilot sample (per shots) and whatever the main pass bought it (al shots)
                idx_all = idx_live
                s_all = al[idx_all].astype(np.int64)
                p_all = np.clip((1.0 + means[idx_all]) / 2.0, 0.0, 1.0)
                c_all = coeffs[idx_all]
                mp = m_pilot[idx_all]
                denom = (per + s_all).astype(float)
                for r_i in range(REPEATS):
                    kk = rng.binomial(np.maximum(s_all, 0), p_all)
                    m_main = np.where(s_all > 0, (2.0 * kk - s_all) / np.maximum(s_all, 1), 0.0)
                    m_pool = (per * mp + s_all * m_main) / denom
                    vals[r_i] = ident + float(np.dot(c_all, m_pool))
            else:
                for r_i in range(REPEATS):
                    kk = rng.binomial(s, pf)
                    vals[r_i] = base + float(np.dot(c_f, (2.0 * kk - s) / s))
            uses_pilot = name in ("naive", "retain", "shrunk", "fixed", "pooled", "best")
            out[name] = {
                "std_mha": float(vals.std(ddof=1) * 1000),
                "bias_mha": float((vals.mean() - e_true) * 1000),
                "rmse_mha": float(np.sqrt(np.mean((vals - e_true) ** 2)) * 1000),
                "shots": int(al.sum()) + (pilot if uses_pilot else 0),
                "terms_funded": nlive if name in ("pooled", "best") else int((al > 0).sum()),
            }

        rec.update({
            "n_terms": L, "n_qubits": n, "n_live_terms": nlive,
            "lambda": float(a.sum()),
            "zero_variance_terms": int(((sigma < 1e-9) & live).sum()),
            "exact_energy": e_true,
            "schemes": out,
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
        print("%-24s L=%-4d | uni %8.3f  naive %10.2f  fixed %8.3f  best %8.3f  oracle %8.3f"
              % (tag, rec["n_terms"], s["uniform"]["rmse_mha"], s["naive"]["rmse_mha"],
                 s["fixed"]["rmse_mha"], s["best"]["rmse_mha"], s["oracle"]["rmse_mha"]))
    else:
        print("%-24s ERROR %s" % (tag, rec["traceback"].strip().splitlines()[-1][:80]))


if __name__ == "__main__":
    main()
