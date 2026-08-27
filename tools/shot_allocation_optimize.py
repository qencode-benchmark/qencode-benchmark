#!/usr/bin/env python
"""Does a better shot-allocation scheme rescue the collapsing LiH optimisation runs?

The estimator study (experiments/shot_allocation) showed that Neyman allocation with
shrinkage and pooling cuts energy RMSE by ~1.5x at equal cost. That is a statement about
the estimator alone. This asks the question that actually matters: does feeding an
optimiser the cleaner signal change the OUTCOME of the optimisation?

The target is the archived failure: LiH, L-BFGS-B, 1000 shots per commuting group,
budget 100 -- ten seeds, all landing at 685-710 mHa. Those runs stopped after 14
evaluations, which is fewer than the 16 needed for a single finite-difference gradient
over 15 parameters, so the state never left Hartree-Fock.

Two explanations are confounded in that failure and this design separates them:
  (a) the optimiser needed MORE STEPS  -> more evaluations at the same noise fixes it
  (b) the optimiser needed a CLEANER SIGNAL -> same evaluations at lower noise fixes it

so the budget axis carries three points:
  A  total 1e7, 1e5 per eval ->  100 evals   (replicates the original scale)
  B  total 1e8, 1e5 per eval -> 1000 evals   (10x the steps, same noise)
  C  total 1e8, 1e6 per eval ->  100 evals   (same steps, 10x cleaner)

Every scheme is charged exactly `per_eval` shots per energy evaluation -- Neyman pays
for its pilot out of that, not on top -- so a row of this table is a fair comparison at
identical measurement cost. Actual shots consumed are counted and reported, not assumed.

    python opt_job.py <mol> <optimizer> <scheme> <total> <per_eval> <seed> <outdir>

`scheme` may also be `exact`, which bypasses sampling entirely. Those runs are the
calibration control: an optimiser that cannot solve the molecule with perfect arithmetic
has a hyperparameter problem, not a noise problem, and its noisy runs prove nothing.
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
PILOT_FRAC = 0.10
P = {"X": qml.PauliX, "Y": qml.PauliY, "Z": qml.PauliZ}


class BudgetExhausted(Exception):
    pass


def build(mol, repo):
    f = sorted(glob.glob(os.path.join(repo, "releases/v4/db/%s_ccpvdz_JW_HEA*.json" % mol)))[0]
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
    return {
        "coeffs": np.array([t["coefficient"] for t in h["pauli_terms"]], dtype=float),
        "obs": [op(t["pauli_string"]) for t in h["pauli_terms"]],
        "n": h["num_qubits"],
        "hf": d["artifacts"]["circuits"]["hf_state"],
        "e_exact": d["results"]["reference"]["exact_qubit_ground_energy_hartree"],
        "entry_id": d["entry_id"],
        "nterms": len(h["pauli_terms"]),
    }


class Energy(object):
    """Energy oracle with a shot budget, a per-evaluation allocation scheme, and a counter.

    Sampling draws each Pauli term from Binomial(s, (1+<P>)/2). For a +-1 observable that
    is the exact sampling distribution (validated against circuit execution in
    experiments/shot_allocation/binomial_check.py), which is what makes a 500-run grid of
    full optimisations affordable.
    """

    def __init__(self, info, scheme, total, per_eval, seed):
        self.c = info["coeffs"]
        self.obs = info["obs"]
        self.n = info["n"]
        self.hf = np.array(info["hf"])
        self.scheme = scheme
        self.total = total
        self.per_eval = per_eval
        self.rng = np.random.default_rng(10000 + seed)
        self.shots_used = 0
        self.n_evals = 0
        self.trace = []
        self.live = np.array([o is not None for o in self.obs])
        self.nlive = int(self.live.sum())
        self.a = np.abs(self.c)
        self.ident = float(self.c[~self.live].sum()) if (~self.live).any() else 0.0
        self.idx = np.nonzero(self.live)[0]
        self.c_live = self.c[self.idx]

        self.dev = qml.device("default.qubit", wires=self.n)
        Hops = [o if o is not None else qml.Identity(0) for o in self.obs]
        self.H = qml.Hamiltonian(list(self.c), Hops)

        @qml.qnode(self.dev)
        def _exact(p):
            self._circ(p)
            return qml.expval(self.H)

        @qml.qnode(self.dev)
        def _all(p):
            self._circ(p)
            return [qml.expval(o) for o in Hops]

        self._exact = _exact
        self._all = _all

        # uniform / weighted allocations are state-independent, so build them once
        pe = per_eval
        self.alloc_uniform = np.where(self.live, pe // max(self.nlive, 1), 0).astype(np.int64)
        w = self.a * self.live
        self.alloc_weighted = np.floor(w / max(w.sum(), 1e-300) * pe).astype(np.int64)
        self.pilot = int(pe * PILOT_FRAC)
        self.per_pilot = max(2, self.pilot // max(self.nlive, 1))

    def _circ(self, p):
        qml.BasisState(self.hf, wires=range(self.n))
        i = 0
        for _ in range(REPS):
            for w in range(self.n):
                qml.RY(p[i], wires=w); i += 1
            for w in range(self.n - 1):
                qml.CNOT(wires=[w, w + 1])
        for w in range(self.n):
            qml.RY(p[i], wires=w); i += 1

    def exact(self, p):
        return float(self._exact(p))

    def __call__(self, p):
        p = np.asarray(p, dtype=float)
        if self.scheme == "exact":
            self.n_evals += 1
            v = float(self._exact(p))
            self.trace.append(v)
            return v
        if self.shots_used + self.per_eval > self.total:
            raise BudgetExhausted()

        means = np.array([float(x) for x in self._all(p)])
        m_live = means[self.idx]
        p1 = np.clip((1.0 + m_live) / 2.0, 0.0, 1.0)

        if self.scheme == "uniform":
            al = self.alloc_uniform
        elif self.scheme == "weighted":
            al = self.alloc_weighted
        elif self.scheme == "neyman":
            # pilot pass, charged out of per_eval, with Agresti-Coull shrinkage so that
            # no term can be assigned an estimated sigma of exactly zero and starved
            k0 = self.rng.binomial(self.per_pilot, p1)
            m_pilot = (2.0 * k0 - self.per_pilot) / float(self.per_pilot)
            p_ac = (k0 + 1.0) / (self.per_pilot + 2.0)
            sig = 2.0 * np.sqrt(p_ac * (1.0 - p_ac))
            wgt = np.zeros(len(self.c))
            wgt[self.idx] = self.a[self.idx] * sig
            rest = self.per_eval - self.pilot - self.nlive
            base = np.where(self.live, 1, 0).astype(np.int64)
            if rest > 0:
                al = base + np.floor(wgt / max(wgt.sum(), 1e-300) * rest).astype(np.int64)
            else:
                al = base
        else:
            raise ValueError("unknown scheme " + self.scheme)

        s = al[self.idx].astype(np.int64)
        kk = self.rng.binomial(np.maximum(s, 0), p1)
        m_main = np.where(s > 0, (2.0 * kk - s) / np.maximum(s, 1), 0.0)

        if self.scheme == "neyman":
            # pool the pilot with the main pass: it is already paid for
            denom = (self.per_pilot + s).astype(float)
            m_use = (self.per_pilot * m_pilot + s * m_main) / denom
            spent = int(s.sum()) + self.pilot
        else:
            m_use = m_main
            spent = int(s.sum())

        self.shots_used += spent
        self.n_evals += 1
        v = self.ident + float(np.dot(self.c_live, m_use))
        self.trace.append(v)
        return v


def run_spsa(E, x0, max_evals, a=2.0, c=0.1, alpha=0.602, gamma=0.101, out=None):
    """Textbook SPSA. Two energy evaluations per iteration regardless of dimension,
    which is the reason it is the standard recommendation for noisy VQE."""
    x = np.array(x0, dtype=float)
    A = max(1.0, 0.1 * max_evals / 2.0)
    rng = np.random.default_rng(777)
    k = 0
    while True:
        ak = a / (k + 1 + A) ** alpha
        ck = c / (k + 1) ** gamma
        d = rng.choice([-1.0, 1.0], size=x.size)
        fp = E(x + ck * d)
        fm = E(x - ck * d)
        g = (fp - fm) / (2.0 * ck) * d
        x = x - ak * g
        if out is not None:
            out[0] = np.array(x)
        k += 1
    return x


def main():
    mol, opt, scheme, total_s, per_s, seed_s, outdir = sys.argv[1:8]
    total, per_eval, seed = int(total_s), int(per_s), int(seed_s)
    repo = os.environ.get("QENCODE_REPO", os.getcwd())
    tag = "%s_%s_%s_T%d_P%d_s%d" % (mol, opt, scheme, total, per_eval, seed)
    rec = {"molecule": mol, "optimizer": opt, "scheme": scheme, "total_shots_budget": total,
           "shots_per_eval": per_eval, "seed": seed, "tag": tag, "reps": REPS,
           "provenance": _provenance(),
           "pennylane": qml.__version__}
    t0 = time.time()
    try:
        info = build(mol, repo)
        n = info["n"]
        npar = n * (REPS + 1)
        x0 = np.random.default_rng(seed).uniform(-0.1, 0.1, size=npar)
        E = Energy(info, scheme, total, per_eval, seed)
        max_evals = total // per_eval
        rec.update({"n_qubits": n, "n_terms": info["nterms"], "n_params": npar,
                    "entry_id": info["entry_id"],
                    "exact_energy_hartree": info["e_exact"],
                    "max_evals": max_evals})

        hard_cap = max_evals
        seen = {"best_noisy": float("inf"), "best_params": np.array(x0),
                "last_params": np.array(x0)}

        def f(p):
            if E.n_evals >= hard_cap:
                raise BudgetExhausted()
            v = E(p)
            seen["last_params"] = np.array(p, dtype=float)
            if v < seen["best_noisy"]:
                seen["best_noisy"] = v
                seen["best_params"] = np.array(p, dtype=float)
            return v

        # When the budget runs out mid-call the exception unwinds straight past any
        # assignment after minimize(), so the final point must be captured from inside
        # the callback, never from the optimizer return value alone.
        xfin = None
        spsa_x = [np.array(x0)]
        # `_r` = refuse to stop: zero tolerances so the optimiser cannot declare
        # convergence, plus restart from its own final point if it returns anyway.
        restart = opt.endswith("_r")
        base_opt = opt[:-2] if restart else opt
        rec["refuse_to_stop"] = restart
        restarts = [0]

        def grad_ps(p):
            g = np.zeros(npar)
            for i in range(npar):
                e = np.zeros(npar); e[i] = np.pi / 2.0
                g[i] = (f(p + e) - f(p - e)) / 2.0
            return g

        termination = []

        def _log_stop(r):
            """One optimiser return: how far in, and what scipy said about it."""
            termination.append({
                "evals_at_stop": E.n_evals,
                "status": int(getattr(r, "status", -1)),
                "message": str(getattr(r, "message", ""))[:120],
            })

        def once(x):
            rem = max(1, hard_cap - E.n_evals)
            if base_opt == "COBYLA":
                kw = {"tol": 1e-14} if restart else {}
                r = minimize(f, x, method="COBYLA",
                             options={"maxiter": rem, "rhobeg": 0.3}, **kw)
                _log_stop(r)
                return np.array(r.x)
            if base_opt == "LBFGSB":
                o = {"maxfun": rem, "maxiter": rem}
                if restart:
                    o.update({"ftol": 0.0, "gtol": 0.0})
                r = minimize(f, x, method="L-BFGS-B", options=o)
                _log_stop(r)
                return np.array(r.x)
            if base_opt == "LBFGSB_ps":
                o = {"maxfun": rem, "maxiter": rem}
                if restart:
                    o.update({"ftol": 0.0, "gtol": 0.0})
                r = minimize(f, x, method="L-BFGS-B", jac=grad_ps, options=o)
                _log_stop(r)
                return np.array(r.x)
            raise ValueError("no restart form for " + base_opt)

        try:
            if base_opt in ("COBYLA", "LBFGSB", "LBFGSB_ps"):
                x = np.array(x0, dtype=float)
                while True:
                    before = E.n_evals
                    x = once(x)
                    xfin = np.array(x)
                    if not restart:
                        break
                    spent = E.n_evals - before
                    restarts[0] += 1
                    # a restart that buys no evaluations would spin forever
                    if spent < 2 or E.n_evals >= hard_cap:
                        break
            elif opt == "__never__":
                pass
            elif opt == "Adam":
                x = np.array(x0, dtype=float)
                m = np.zeros(npar); v2 = np.zeros(npar)
                b1, b2, eps, lr = 0.9, 0.999, 1e-8, 0.15
                t = 0
                while True:
                    g = np.zeros(npar)
                    for i in range(npar):
                        e = np.zeros(npar); e[i] = np.pi / 2.0
                        g[i] = (f(x + e) - f(x - e)) / 2.0
                    t += 1
                    m = b1 * m + (1 - b1) * g
                    v2 = b2 * v2 + (1 - b2) * g * g
                    x = x - lr * (m / (1 - b1 ** t)) / (np.sqrt(v2 / (1 - b2 ** t)) + eps)
                    xfin = np.array(x)
            elif opt == "SPSA":
                # gains are calibrated at zero noise before any noisy run is believed;
                # see experiments/shot_allocation_opt/spsa_calibration.txt
                run_spsa(f, x0, hard_cap,
                         a=float(os.environ.get("SPSA_A", "2.0")),
                         c=float(os.environ.get("SPSA_C", "0.1")), out=spsa_x)
                xfin = spsa_x[0]
            else:
                raise ValueError("unknown optimizer " + opt)
        except BudgetExhausted:
            pass
        except StopIteration:
            pass
        if opt == "SPSA":
            xfin = spsa_x[0]
        if xfin is None:
            xfin = seen["last_params"]

        # for every optimiser the honest answer is the exact energy at the parameters
        # it would actually hand back, not the noisy value it happened to believe
        e_true_final = E.exact(xfin)
        e_true_best = E.exact(seen["best_params"])
        rec.update({
            "evaluations": E.n_evals,
            "restarts": restarts[0],
            "termination": termination,
            "n_terminations": len(termination),
            "shots_consumed": E.shots_used,
            "believed_energy_hartree": (None if seen["best_noisy"] == float("inf")
                                        else seen["best_noisy"]),
            "final_energy_hartree": e_true_final,
            "best_energy_hartree": e_true_best,
            "gap_final_mha": abs(e_true_final - info["e_exact"]) * 1000,
            "gap_best_mha": abs(e_true_best - info["e_exact"]) * 1000,
            "seconds": round(time.time() - t0, 1),
            "status": "ok",
        })
    except Exception:
        rec.update({"status": "error", "traceback": traceback.format_exc()[-900:],
                    "seconds": round(time.time() - t0, 1)})

    os.makedirs(outdir, exist_ok=True)
    json.dump(rec, open(os.path.join(outdir, tag + ".json"), "w"), indent=1)
    if rec["status"] == "ok":
        print("%-44s evals=%5d shots=%11d  gap_final=%9.2f  gap_best=%9.2f mHa"
              % (tag, rec["evaluations"], rec["shots_consumed"],
                 rec["gap_final_mha"], rec["gap_best_mha"]))
    else:
        print("%-44s ERROR %s" % (tag, rec["traceback"].strip().splitlines()[-1][:70]))


if __name__ == "__main__":
    main()
