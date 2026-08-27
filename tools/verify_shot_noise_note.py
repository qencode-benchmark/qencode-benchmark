#!/usr/bin/env python
"""Recompute every figure quoted in docs/SHOT_NOISE_AND_ALLOCATION.md from the committed
data. Each check prints the value in the note, the value from the data, and PASS or FAIL.
"""
import glob
import json
import os
import sys

import numpy as np

R = os.environ.get("QENCODE_REPO", os.getcwd())
FAILS = []


def load(rel):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(R, rel, "*.json")))]


def check(label, claimed, actual, tol=0.02):
    if actual is None:
        ok = False
    elif isinstance(claimed, str):
        ok = claimed == actual
    else:
        ok = abs(actual - claimed) <= max(tol * abs(claimed), tol)
    tag = "PASS" if ok else "FAIL"
    if not ok:
        FAILS.append(label)
    a = actual if isinstance(actual, str) else ("%.2f" % actual if actual is not None else "?")
    c = claimed if isinstance(claimed, str) else "%.2f" % claimed
    print("  [%s] %-56s note=%-10s data=%s" % (tag, label, c, a))


# ---------------------------------------------------------------- estimator study
est = [r for r in load("experiments/shot_allocation/final") if r.get("status") == "ok"]
print("\nESTIMATOR STUDY  (%d runs)" % len(est))
check("n runs", 90, float(len(est)))
def rmse(r, k):
    return r["schemes"][k]["rmse_mha"]
for k, claimed in (("uniform", 11.35), ("weighted", 9.68), ("naive", 603.70),
                   ("shrunk", 8.88), ("best", 8.49), ("oracle", 7.41)):
    check("median RMSE %s" % k, claimed, float(np.median([rmse(r, k) for r in est])))
for k, claimed in (("weighted", 58), ("naive", 22), ("shrunk", 81), ("best", 84), ("oracle", 86)):
    n = sum(1 for r in est if rmse(r, "uniform") / max(rmse(r, k), 1e-12) > 1)
    check("beats uniform %s" % k, float(claimed), float(n), tol=0.001)
check("median std naive", 5.75, float(np.median([r["schemes"]["naive"]["std_mha"] for r in est])))
check("median std uniform", 11.36, float(np.median([r["schemes"]["uniform"]["std_mha"] for r in est])))
rel = np.array([rmse(r, "uniform") / max(rmse(r, "best"), 1e-12) for r in est])
check("best vs uniform ratio", 1.53, float(np.median(rel)))
check("shots equivalent (ratio squared)", 2.33, float(np.median(rel) ** 2))
kil = [r["diagnostic"]["mean_abs_c_killed"] / max(r["diagnostic"]["mean_abs_c_kept"], 1e-12)
       for r in est if r["diagnostic"]["n_sigma_hat_zero"] > 0]
check("killed terms x mean |c|", 9.1, float(np.median(kil)))
frac = [r["diagnostic"]["sum_abs_c_killed"] / max(r["diagnostic"]["lambda"], 1e-12) for r in est]
check("share of lambda dropped (%)", 48.0, float(100 * np.median(frac)))

# ---------------------------------------------------------------- LiH at 100 evals
grid = [r for r in load("experiments/shot_allocation_opt/grid") if r.get("status") == "ok"]
print("\nLiH / L-BFGS-B AT 100 EVALUATIONS  (from %d optimisation runs)" % len(grid))
def med(recs, mol, opt, sch, T, P, field="gap_best_mha"):
    v = [r[field] for r in recs if r["molecule"] == mol and r["optimizer"] == opt
         and r["scheme"] == sch and r["total_shots_budget"] == T and r["shots_per_eval"] == P]
    return float(np.median(v)) if v else None
for sch, claimed in (("uniform", 707.85), ("weighted", 708.42), ("neyman", 707.19), ("exact", 651.67)):
    check("LiH LBFGSB 100ev %s" % sch, claimed, med(grid, "LiH", "LBFGSB", sch, 10**7, 10**5))
u = med(grid, "LiH", "LBFGSB", "uniform", 10**7, 10**5)
e = med(grid, "LiH", "LBFGSB", "exact", 10**7, 10**5)
check("noise share of the 707 (%)", 8.0, float(100 * (u - e) / u), tol=0.15)

# ---------------------------------------------------------------- the 2x2
ctl = [r for r in load("experiments/shot_allocation_opt/early_stopping_control") if r.get("status") == "ok"]
print("\nTHE 2x2  (%d runs)" % len(ctl))
def m2(mol, opt, sch):
    v = [r["gap_best_mha"] for r in ctl if r["molecule"] == mol and r["optimizer"] == opt
         and r["scheme"] == sch]
    return float(np.median(v)) if v else None
for mol, opt, sch, claimed in (
        ("H2O", "COBYLA", "uniform", 982.82), ("H2O", "COBYLA_r", "uniform", 586.55),
        ("H2O", "COBYLA", "neyman", 952.70), ("H2O", "COBYLA_r", "neyman", 17.55),
        ("LiH", "LBFGSB_ps", "uniform", 408.97), ("LiH", "LBFGSB_ps_r", "uniform", 398.93),
        ("LiH", "LBFGSB_ps", "neyman", 14.88), ("LiH", "LBFGSB_ps_r", "neyman", 3.84),
        ("H2O", "LBFGSB_ps_r", "uniform", 3.97), ("H2O", "LBFGSB_ps_r", "neyman", 5.63),
        ("LiH", "LBFGSB_r", "uniform", 707.59), ("H2O", "LBFGSB_r", "uniform", 1052.21)):
    check("2x2 %s/%s/%s" % (mol, opt, sch), claimed, m2(mol, opt, sch))
a = m2("LiH", "LBFGSB_ps", "uniform"); b = m2("LiH", "LBFGSB_ps_r", "uniform")
c = m2("LiH", "LBFGSB_ps", "neyman")
check("free fix recovers (% of neyman gain)", 3.0, float(100 * (a - b) / (a - c)), tol=0.4)
h = m2("H2O", "COBYLA", "uniform") / m2("H2O", "COBYLA_r", "neyman")
check("H2O COBYLA both-fixes factor", 56.0, float(h), tol=0.05)

# ---------------------------------------------------------------- scaling / success rates
sc = [r for r in load("experiments/shot_allocation_opt/budget_scaling") if r.get("status") == "ok"]
print("\nBUDGET SCALING  (%d runs)" % len(sc))
def succ(mol, opt, sch, T):
    v = [r["gap_best_mha"] for r in sc if r["molecule"] == mol and r["optimizer"] == opt
         and r["scheme"] == sch and r["total_shots_budget"] == T]
    return float(sum(1 for x in v if x < 10.0)) if v else None
for mol, opt, sch, T, claimed in (
        ("H2O", "COBYLA_r", "exact", 10**7, 5), ("H2O", "COBYLA_r", "exact", 3 * 10**7, 10),
        ("H2O", "COBYLA_r", "neyman", 10**8, 2), ("H2O", "COBYLA_r", "uniform", 10**8, 0),
        ("LiH", "LBFGSB_ps_r", "neyman", 10**8, 7), ("LiH", "LBFGSB_ps_r", "weighted", 10**8, 3),
        ("LiH", "LBFGSB_ps_r", "uniform", 10**8, 0), ("LiH", "LBFGSB_ps_r", "exact", 10**8, 10)):
    check("success %s/%s/%s @%.0e" % (mol, opt, sch, T), float(claimed), succ(mol, opt, sch, T), tol=0.001)
# nothing works below 1e8
below = 0
for T in (10**6, 3 * 10**6, 10**7, 3 * 10**7):
    for mol in ("LiH", "H2O"):
        for opt in ("COBYLA_r", "LBFGSB_ps_r"):
            for sch in ("uniform", "weighted", "neyman"):
                s = succ(mol, opt, sch, T)
                if s:
                    below += s
check("noisy successes below 1e8 (all cells)", 1.0, float(below), tol=0.001)
# abrupt onset
def r_(T):
    return med(sc, "LiH", "LBFGSB_ps_r", "uniform", T, 10**5) / med(sc, "LiH", "LBFGSB_ps_r", "neyman", T, 10**5)
check("LiH PS ratio @1e6", 1.01, r_(10**6))
check("LiH PS ratio @3e7", 1.06, r_(3 * 10**7))
check("LiH PS ratio @1e8", 104.0, r_(10**8), tol=0.05)

# per-seed list quoted in the note
per = sorted(r["gap_best_mha"] for r in sc if r["molecule"] == "LiH"
             and r["optimizer"] == "LBFGSB_ps_r" and r["scheme"] == "neyman"
             and r["total_shots_budget"] == 10**8)
quoted = [1.5, 2.3, 2.8, 3.5, 3.5, 4.2, 4.8, 26.3, 176.7, 255.9]
ok = len(per) == 10 and all(abs(a - b) < 0.15 for a, b in zip(quoted, per))
print("  [%s] %-56s note=%s" % ("PASS" if ok else "FAIL", "per-seed list (LiH PS 1e8 neyman)",
                                " ".join("%.1f" % x for x in quoted)))
print("  %-63s data=%s" % ("", " ".join("%.1f" % x for x in per)))
if not ok:
    FAILS.append("per-seed list")

# ---------------------------------------------------------------- termination
tm = [r for r in load("experiments/shot_allocation_opt/early_stopping_numbers") if r.get("status") == "ok"]
print("\nTERMINATION  (%d runs)" % len(tm))
def first(mol, opt, sch, P):
    # A run that never declared convergence is counted at its full evaluation count,
    # matching the note. Filtering those out would report only the runs that stopped,
    # which is a different quantity and reads lower.
    v = [(r["termination"][0]["evals_at_stop"] if r.get("termination") else r["evaluations"])
         for r in tm if r["molecule"] == mol and r["optimizer"] == opt
         and r["scheme"] == sch and r["shots_per_eval"] == P]
    return float(np.median(v)) if v else None


def never(mol, opt, sch, P):
    rs = [r for r in tm if r["molecule"] == mol and r["optimizer"] == opt
          and r["scheme"] == sch and r["shots_per_eval"] == P]
    return float(sum(1 for r in rs if not r.get("termination"))) if rs else None
for mol, P, claimed in (("H2O", 10**3, 318), ("H2O", 10**5, 325), ("H2O", 10**7, 292),
                        ("LiH", 10**3, 400), ("LiH", 10**7, 392)):
    check("FD first stop %s @%.0e" % (mol, P), float(claimed), first(mol, "LBFGSB", "uniform", P), tol=0.05)
for mol, P, claimed in (("H2O", 10**3, 237), ("H2O", 10**7, 825),
                        ("LiH", 10**3, 325), ("LiH", 10**7, 1000)):
    check("PS first stop %s @%.0e" % (mol, P), float(claimed), first(mol, "LBFGSB_ps", "uniform", P), tol=0.05)
ex = [r["termination"][0]["evals_at_stop"] for r in tm if r["molecule"] == "H2O"
      and r["optimizer"] == "LBFGSB" and r["scheme"] == "exact" and r.get("termination")]
check("FD H2O exact", 403.0, float(np.median(ex)), tol=0.05)
# 100% of PS terminations are "no further decrease"
msgs = [e["message"].upper() for r in tm if r["optimizer"].startswith("LBFGSB_ps")
        for e in r.get("termination", [])]
share = 100.0 * sum(1 for m in msgs if "REL_REDUCTION" in m) / max(len(msgs), 1)
check("PS 'no further decrease' share (%)", 100.0, share, tol=0.01)
# neyman delays the first stop on LiH PS
check("LiH PS first stop @1e5 uniform", 310.0, first("LiH", "LBFGSB_ps", "uniform", 10**5), tol=0.05)
check("LiH PS first stop @1e5 neyman", 822.0, first("LiH", "LBFGSB_ps", "neyman", 10**5), tol=0.05)
for mol, P, claimed in (("LiH", 10**5, 0), ("LiH", 10**6, 4), ("LiH", 10**7, 7), ("H2O", 10**7, 1)):
    check("never declared PS %s @%.0e" % (mol, P), float(claimed),
          never(mol, "LBFGSB_ps", "uniform", P), tol=0.001)
for opt in ("LBFGSB", "COBYLA"):
    tot = sum(never(m, opt, "uniform", P) for m in ("LiH", "H2O")
              for P in (10**3, 10**4, 10**5, 10**6, 10**7))
    check("never declared %s (all cells)" % opt, 0.0, float(tot), tol=0.001)

# ---------------------------------------------------------------- SPSA
sp = [r for r in load("experiments/shot_allocation_opt/spsa_calibration") if r.get("status") == "ok"]
print("\nSPSA CALIBRATION  (%d runs)" % len(sp))
best = min(sp, key=lambda r: r["gap_best_mha"])
check("best SPSA gap", 1.97, best["gap_best_mha"])
print("      best config file suggests a=5.0 c=0.1; gap_best=%.2f" % best["gap_best_mha"])

print("\n" + "=" * 78)
if FAILS:
    print("FAILED CHECKS (%d):" % len(FAILS))
    for f in FAILS:
        print("   -", f)
    sys.exit(1)
print("ALL CHECKS PASS")
