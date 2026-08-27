#!/usr/bin/env python
"""Budget scaling curves: at what budget does allocation quality start to matter?

Reports, per (molecule, optimiser), the median gap for each scheme against total shot
budget, plus two derived quantities:

  crossover  the smallest budget at which neyman beats uniform by more than the seed
             spread, i.e. the point where paying for variance estimation starts to buy
             something real rather than noise
  headroom   how much of the exact-arithmetic ceiling each scheme has closed, which
             separates "allocation is limiting" from "evaluations are limiting"
"""
import json, glob, os, sys
import numpy as np

d = sys.argv[1] if len(sys.argv) > 1 else "."
recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]
ok = [r for r in recs if r.get("status") == "ok"]
bad = [r for r in recs if r.get("status") != "ok"]
print("loaded %d (%d ok, %d error)" % (len(recs), len(ok), len(bad)))
for r in bad[:6]:
    print("  ERROR", r["tag"], r.get("traceback", "").strip().splitlines()[-1][:90])
print()

SCH = ["uniform", "weighted", "neyman", "exact"]
BUDGETS = sorted(set(r["total_shots_budget"] for r in ok))
OPTS = ["COBYLA_r", "LBFGSB_ps_r", "COBYLA", "LBFGSB_ps"]


def vals(mol, opt, sch, T, field="gap_best_mha"):
    return np.array([r[field] for r in ok if r["molecule"] == mol and r["optimizer"] == opt
                     and r["scheme"] == sch and r["total_shots_budget"] == T])


def med(mol, opt, sch, T, field="gap_best_mha"):
    v = vals(mol, opt, sch, T, field)
    return np.median(v) if v.size else float("nan")


def lab(T):
    return "%-5s(%4d ev)" % ("%.0eS" % T, T // 100000)


for mol in sorted(set(r["molecule"] for r in ok)):
    for opt in OPTS:
        if not vals(mol, opt, "uniform", BUDGETS[0]).size:
            continue
        print("=" * 112)
        print("%s / %s   median gap over 10 seeds, mHa   (1e5 shots per evaluation)"
              % (mol, opt))
        print("=" * 112)
        print("%-18s %10s %10s %10s %10s | %10s %10s"
              % ("total budget", "uniform", "weighted", "neyman", "exact",
                 "ney/uni", "ney vs exact"))
        print("-" * 112)
        for T in BUDGETS:
            u, w, n, e = [med(mol, opt, s, T) for s in SCH]
            if np.isnan(u):
                continue
            ratio = u / n if n > 0 else float("nan")
            hd = n - e
            print("%-18s %10.2f %10.2f %10.2f %10.2f | %9.2fx %+10.2f"
                  % (lab(T), u, w, n, e, ratio, hd))
        print()

print("=" * 112)
print("CROSSOVER -- smallest budget where neyman beats uniform by more than the seed spread")
print("  (paired over seeds; the gate is median improvement > the interquartile range of")
print("   the per-seed differences, so a win has to be bigger than run-to-run variation)")
print("=" * 112)
print("%-5s %-14s %-22s %-14s %s" % ("mol", "optimizer", "crossover budget", "gain there", "gain at 1e8"))
print("-" * 112)
for mol in sorted(set(r["molecule"] for r in ok)):
    for opt in OPTS:
        if not vals(mol, opt, "uniform", BUDGETS[0]).size:
            continue
        cross, cgain = None, None
        for T in BUDGETS:
            u = vals(mol, opt, "uniform", T)
            n = vals(mol, opt, "neyman", T)
            if u.size != n.size or not u.size:
                continue
            diff = u - n                      # positive = neyman better, paired by seed
            iqr = np.subtract(*np.percentile(diff, [75, 25]))
            if np.median(diff) > max(abs(iqr), 1.0):
                cross, cgain = T, np.median(diff)
                break
        big = med(mol, opt, "uniform", BUDGETS[-1]) - med(mol, opt, "neyman", BUDGETS[-1])
        print("%-5s %-14s %-22s %-14s %+.2f mHa"
              % (mol, opt,
                 ("%.0e shots (%d ev)" % (cross, cross // 100000)) if cross else "never in this range",
                 ("%+.2f mHa" % cgain) if cross else "-", big))

print()
print("=" * 112)
print("WHAT IS LIMITING?  share of the exact-arithmetic ceiling still unclosed by neyman")
print("  small  -> allocation is nearly as good as perfect arithmetic; evaluations limit you")
print("  large  -> measurement is what is holding the run back")
print("=" * 112)
print("%-5s %-14s %s" % ("mol", "optimizer", "  ".join("%12s" % lab(T) for T in BUDGETS)))
print("-" * 112)
for mol in sorted(set(r["molecule"] for r in ok)):
    for opt in OPTS:
        if not vals(mol, opt, "uniform", BUDGETS[0]).size:
            continue
        cells = []
        for T in BUDGETS:
            n, e = med(mol, opt, "neyman", T), med(mol, opt, "exact", T)
            cells.append("%12s" % ("%.0f%%" % (100.0 * (n - e) / n) if n > 0 else "-"))
        print("%-5s %-14s %s" % (mol, opt, "  ".join(cells)))

print()
print("=" * 112)
print("EVALUATIONS ACTUALLY SPENT (uniform) -- confirms the _r series is unconfounded")
print("=" * 112)
print("%-5s %-14s %s" % ("mol", "optimizer", "  ".join("%12s" % lab(T) for T in BUDGETS)))
print("-" * 112)
for mol in sorted(set(r["molecule"] for r in ok)):
    for opt in OPTS:
        if not vals(mol, opt, "uniform", BUDGETS[0]).size:
            continue
        cells = ["%12s" % ("%d/%d" % (med(mol, opt, "uniform", T, "evaluations"), T // 100000))
                 for T in BUDGETS]
        print("%-5s %-14s %s" % (mol, opt, "  ".join(cells)))

print()
print("=" * 112)
print("SUCCESS RATE -- the right curve, because the outcome is bimodal")
print("  Per-seed results do not improve smoothly with budget: a run either catches and")
print("  converges or stays stuck near its starting energy, so the median of a 10-seed")
print("  set hides the shape. What actually scales is the FRACTION of runs that converge.")
print("  Cell = seeds reaching < 10 mHa (the certification threshold) out of 10.")
print("=" * 112)
for mol in sorted(set(r["molecule"] for r in ok)):
    for opt in OPTS:
        if not vals(mol, opt, "uniform", BUDGETS[0]).size:
            continue
        print()
        print("  %s / %s" % (mol, opt))
        print("  %-10s %s" % ("scheme", "  ".join("%12s" % lab(T) for T in BUDGETS)))
        print("  " + "-" * 106)
        for sch in SCH:
            cells = []
            for T in BUDGETS:
                v = vals(mol, opt, sch, T)
                cells.append("%12s" % ("%d/10" % (v < 10.0).sum() if v.size else "-"))
            print("  %-10s %s" % (sch, "  ".join(cells)))

print()
print("=" * 112)
print("WIN RATE -- how often neyman beats uniform, paired by seed (a bimodal-safe statistic)")
print("=" * 112)
print("%-5s %-14s %s" % ("mol", "optimizer", "  ".join("%12s" % lab(T) for T in BUDGETS)))
print("-" * 112)
for mol in sorted(set(r["molecule"] for r in ok)):
    for opt in OPTS:
        if not vals(mol, opt, "uniform", BUDGETS[0]).size:
            continue
        cells = []
        for T in BUDGETS:
            u = vals(mol, opt, "uniform", T); n = vals(mol, opt, "neyman", T)
            cells.append("%12s" % ("%d/10" % ((u - n) > 0).sum() if u.size == n.size and u.size else "-"))
        print("%-5s %-14s %s" % (mol, opt, "  ".join(cells)))
