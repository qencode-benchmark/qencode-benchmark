#!/usr/bin/env python
"""Analyse the v2 Neyman grid. Everything is judged on RMSE, so bias counts."""
import json, glob, os, sys
import numpy as np

d = sys.argv[1] if len(sys.argv) > 1 else "."
recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]
ok = [r for r in recs if r.get("status") == "ok"]
bad = [r for r in recs if r.get("status") != "ok"]
print("loaded %d (%d ok, %d error)" % (len(recs), len(ok), len(bad)))
for r in bad:
    print("  ERROR", r["tag"], r.get("traceback", "").strip().splitlines()[-1][:90])
print()

ORDER = ["uniform", "weighted", "naive", "retain", "shrunk", "pooled", "fixed", "best", "oracle"]


def R(r, k):
    return r["schemes"][k]["rmse_mha"]


print("=" * 122)
print("THE FAILURE: does a pilot-estimated sigma kill big-coefficient terms?")
print("=" * 122)
print("%-13s %-10s %9s | %6s %8s | %10s %10s | %8s %8s"
      % ("molecule", "state", "budget", "killed", "of live", "mean|c| kill", "mean|c| keep",
         "sig kill", "sig keep"))
print("-" * 122)
ratios = []
for r in sorted(ok, key=lambda x: (x["n_terms"], x["state"], x["budget"]))[:18]:
    g = r["diagnostic"]
    if g["n_sigma_hat_zero"] == 0:
        continue
    rr = g["mean_abs_c_killed"] / max(g["mean_abs_c_kept"], 1e-12)
    ratios.append(rr)
    print("%-13s %-10s %9d | %6d %8d | %10.5f %10.5f | %8.4f %8.4f"
          % (r["molecule"], r["state"], r["budget"], g["n_sigma_hat_zero"],
             r["n_live_terms"], g["mean_abs_c_killed"], g["mean_abs_c_kept"],
             g["mean_abs_sigma_killed"], g["mean_abs_sigma_kept"]))
allr = [x["diagnostic"]["mean_abs_c_killed"] / max(x["diagnostic"]["mean_abs_c_kept"], 1e-12)
        for x in ok if x["diagnostic"]["n_sigma_hat_zero"] > 0]
frac = [x["diagnostic"]["sum_abs_c_killed"] / max(x["diagnostic"]["lambda"], 1e-12) for x in ok]
print("-" * 122)
print("  across all %d runs with at least one killed term: killed terms carry %.1fx the mean |c|"
      % (len(allr), np.median(allr)))
print("  median share of lambda = sum|c| that gets silently dropped: %.1f%%" % (100 * np.median(frac)))

print()
print("=" * 122)
print("RMSE (mHa) BY SCHEME -- median across all 90 runs, and how often each beats uniform")
print("=" * 122)
print("%-10s %12s %12s %12s %10s" % ("scheme", "median RMSE", "median x uni", "10-90 pct", "beats uni"))
print("-" * 122)
for k in ORDER:
    v = np.array([R(r, k) for r in ok])
    rel = np.array([R(r, "uniform") / max(R(r, k), 1e-12) for r in ok])
    print("%-10s %12.3f %12.2fx %5.2f-%5.2fx %7d/%d"
          % (k, np.median(v), np.median(rel), np.percentile(rel, 10),
             np.percentile(rel, 90), (rel > 1).sum(), len(rel)))

print()
print("=" * 122)
print("THE RECOMMENDED SCHEME (best = shrunk allocation + floor + pooling) BY STATE AND BUDGET -- speedup over uniform at equal cost")
print("=" * 122)
print("%-12s | %-46s | %s" % ("", "vs uniform", "vs weighted"))
for st in ("start", "mid", "converged"):
    sub = [r for r in ok if r["state"] == st]
    if not sub:
        continue
    a = np.array([R(r, "uniform") / max(R(r, "best"), 1e-12) for r in sub])
    b = np.array([R(r, "weighted") / max(R(r, "best"), 1e-12) for r in sub])
    print("%-12s | median %5.2fx  range %4.2f-%5.2fx  wins %2d/%2d | median %5.2fx  wins %2d/%2d"
          % (st, np.median(a), a.min(), a.max(), (a > 1).sum(), len(a),
             np.median(b), (b > 1).sum(), len(b)))
print("-" * 122)
for bg in sorted(set(r["budget"] for r in ok)):
    sub = [r for r in ok if r["budget"] == bg]
    a = np.array([R(r, "uniform") / max(R(r, "best"), 1e-12) for r in sub])
    b = np.array([R(r, "weighted") / max(R(r, "best"), 1e-12) for r in sub])
    print("%-12s | median %5.2fx  range %4.2f-%5.2fx  wins %2d/%2d | median %5.2fx  wins %2d/%2d"
          % ("N=%d" % bg, np.median(a), a.min(), a.max(), (a > 1).sum(), len(a),
             np.median(b), (b > 1).sum(), len(b)))

print()
print("=" * 122)
print("BY MOLECULE (best vs uniform, RMSE ratio)")
print("=" * 122)
for mol in sorted(set(r["molecule"] for r in ok), key=lambda m: [r for r in ok if r["molecule"] == m][0]["n_terms"]):
    sub = [r for r in ok if r["molecule"] == mol]
    a = np.array([R(r, "uniform") / max(R(r, "best"), 1e-12) for r in sub])
    o = np.array([R(r, "uniform") / max(R(r, "oracle"), 1e-12) for r in sub])
    print("  %-12s L=%-5d  best %5.2fx (%4.2f-%5.2f)   oracle ceiling %5.2fx   n=%d"
          % (mol, sub[0]["n_terms"], np.median(a), a.min(), a.max(), np.median(o), len(sub)))

print()
print("=" * 122)
print("SHOT-COST EQUIVALENCE -- variance scales as 1/N, so an r-fold RMSE cut is r^2 fewer shots")
print("=" * 122)
a = np.array([R(r, "uniform") / max(R(r, "best"), 1e-12) for r in ok])
print("  best vs uniform : median %.2fx RMSE  ->  %.2fx fewer shots for the same accuracy"
      % (np.median(a), np.median(a) ** 2))
b = np.array([R(r, "weighted") / max(R(r, "best"), 1e-12) for r in ok])
print("  best vs weighted: median %.2fx RMSE  ->  %.2fx fewer shots" % (np.median(b), np.median(b) ** 2))
c = np.array([R(r, "best") / max(R(r, "oracle"), 1e-12) for r in ok])
print("  best vs oracle  : median %.3fx  (1.0 would mean the pilot costs nothing)" % np.median(c))
