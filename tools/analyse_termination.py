#!/usr/bin/env python
"""Early stopping, as numbers rather than as an explanation.

The behavioural claim so far has been that optimisers with a convergence test mistake
sampling noise for convergence and quit. This measures it directly: at what evaluation
each optimiser stops, how often it declares itself finished, and which scipy termination
condition fires -- all against signal quality, with the evaluation allowance held fixed
at 1000 so nothing is confounded by budget.

    python analyse_term.py <dir>
"""
import json, glob, os, sys, re
import numpy as np

d = sys.argv[1] if len(sys.argv) > 1 else "."
recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]
ok = [r for r in recs if r.get("status") == "ok"]
bad = [r for r in recs if r.get("status") != "ok"]
print("loaded %d (%d ok, %d error)" % (len(recs), len(ok), len(bad)))
for r in bad[:6]:
    print("  ERROR", r["tag"], r.get("traceback", "").strip().splitlines()[-1][:90])
print()

NOISE = sorted(set(r["shots_per_eval"] for r in ok if r["scheme"] != "exact"))
BASES = ["COBYLA", "LBFGSB", "LBFGSB_ps"]


def sel(mol, opt, sch, P=None):
    return [r for r in ok if r["molecule"] == mol and r["optimizer"] == opt
            and r["scheme"] == sch and (P is None or r["shots_per_eval"] == P)]


def short(msg):
    """Collapse scipy termination messages to a comparable label."""
    m = msg.upper()
    if "REL_REDUCTION" in m or "FACTR" in m:
        return "no further decrease"
    if "GRAD" in m and "PROJ" in m:
        return "gradient ~ 0"
    if "LNSRCH" in m or "LINE SEARCH" in m or "ABNORMAL" in m:
        return "line search failed"
    if "MAXITER" in m or "MAXFUN" in m or "MAXIMUM NUMBER" in m or "ITERATION LIMIT" in m:
        return "hit the cap"
    if "OPTIMIZATION TERMINATED" in m or "SUCCES" in m:
        return "cobyla converged"
    return (msg[:26] or "(none)")


print("=" * 116)
print("WHERE DOES IT STOP?  first termination, evaluations of a 1000 cap, default stopping")
print("  median over 10 seeds, with the 10th-90th percentile in brackets")
print("=" * 116)
hdr = "  ".join("%17s" % ("%.0e/eval" % P) for P in NOISE)
print("%-5s %-11s %-9s %s" % ("mol", "optimizer", "scheme", hdr))
print("-" * 116)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        for sch in ("uniform", "neyman"):
            cells = []
            for P in NOISE:
                rs = sel(mol, b, sch, P)
                if not rs:
                    cells.append("%17s" % "-")
                    continue
                v = np.array([x["termination"][0]["evals_at_stop"] if x.get("termination")
                              else x["evaluations"] for x in rs])
                cells.append("%17s" % ("%4d [%4d-%4d]" % (np.median(v),
                                                          np.percentile(v, 10), np.percentile(v, 90))))
            print("%-5s %-11s %-9s %s" % (mol, b, sch, "  ".join(cells)))
    # exact reference
    for b in BASES:
        rs = sel(mol, b, "exact")
        if rs:
            v = np.array([x["termination"][0]["evals_at_stop"] if x.get("termination")
                          else x["evaluations"] for x in rs])
            print("%-5s %-11s %-9s  -> exact arithmetic: %d [%d-%d]"
                  % (mol, b, "exact", np.median(v), np.percentile(v, 10), np.percentile(v, 90)))
    print("-" * 116)

print()
print("=" * 116)
print("HOW OFTEN DOES IT DECLARE ITSELF FINISHED?  terminations per run, refuse-to-stop forms")
print("  each count is one false convergence: the optimiser stopped and was restarted")
print("=" * 116)
print("%-5s %-13s %-9s %s" % ("mol", "optimizer", "scheme", hdr))
print("-" * 116)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        for sch in ("uniform", "neyman"):
            cells = []
            for P in NOISE:
                rs = sel(mol, b + "_r", sch, P)
                if not rs:
                    cells.append("%17s" % "-")
                    continue
                v = np.array([x.get("n_terminations", 0) for x in rs])
                cells.append("%17s" % ("%4.1f [%d-%d]" % (np.median(v), v.min(), v.max())))
            print("%-5s %-13s %-9s %s" % (mol, b + "_r", sch, "  ".join(cells)))
    print("-" * 116)

print()
print("=" * 116)
print("WHY DOES IT STOP?  scipy termination condition, share of all terminations")
print("=" * 116)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        rows = {}
        for P in NOISE:
            counts = {}
            n = 0
            for opt in (b, b + "_r"):
                for sch in ("uniform", "neyman"):
                    for r in sel(mol, opt, sch, P):
                        for e in r.get("termination", []):
                            k = short(e["message"])
                            counts[k] = counts.get(k, 0) + 1
                            n += 1
            rows[P] = (counts, n)
        keys = sorted({k for c, _ in rows.values() for k in c})
        if not keys:
            continue
        print("  %s / %s" % (mol, b))
        print("  %-24s %s" % ("reason", "  ".join("%12s" % ("%.0e" % P) for P in NOISE)))
        print("  " + "-" * 106)
        for k in keys:
            cells = []
            for P in NOISE:
                c, n = rows[P]
                cells.append("%12s" % ("%.0f%%" % (100.0 * c.get(k, 0) / n) if n else "-"))
            print("  %-24s %s" % (k, "  ".join(cells)))
        print()

print("=" * 116)
print("DOES A CLEANER SIGNAL DELAY THE FIRST STOP?  neyman vs uniform, first-stop evaluation")
print("=" * 116)
print("%-5s %-11s %s" % ("mol", "optimizer", hdr))
print("-" * 116)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        cells = []
        for P in NOISE:
            u = sel(mol, b, "uniform", P)
            n = sel(mol, b, "neyman", P)
            if not u or not n:
                cells.append("%17s" % "-")
                continue
            fu = np.median([x["termination"][0]["evals_at_stop"] for x in u if x.get("termination")] or [np.nan])
            fn = np.median([x["termination"][0]["evals_at_stop"] for x in n if x.get("termination")] or [np.nan])
            cells.append("%17s" % ("%4.0f -> %4.0f" % (fu, fn)))
        print("%-5s %-11s %s" % (mol, b, "  ".join(cells)))
