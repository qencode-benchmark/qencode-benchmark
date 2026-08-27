#!/usr/bin/env python
"""Does a better shot-allocation scheme change the OUTCOME of a VQE optimisation?

The comparison that matters is each noisy scheme against the `exact` control at the SAME
evaluation count. If a noisy run matches its exact control, sampling was not the binding
constraint and no allocation scheme can help -- the budget was.
"""
import json, glob, os, sys
import numpy as np

d = sys.argv[1] if len(sys.argv) > 1 else "."
recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]
ok = [r for r in recs if r.get("status") == "ok"]
bad = [r for r in recs if r.get("status") != "ok"]
print("loaded %d (%d ok, %d error)" % (len(recs), len(ok), len(bad)))
for r in bad[:8]:
    print("  ERROR", r["tag"], r.get("traceback", "").strip().splitlines()[-1][:90])
print()

BUD = {(10 ** 7, 10 ** 5): "A  100 evals, 1e5/eval",
       (10 ** 8, 10 ** 5): "B 1000 evals, 1e5/eval",
       (10 ** 8, 10 ** 6): "C  100 evals, 1e6/eval"}
SCH = ["uniform", "weighted", "neyman", "exact"]
OPTS = ["COBYLA", "LBFGSB", "LBFGSB_ps", "Adam", "SPSA"]


def key(r):
    return (r["molecule"], r["optimizer"], r["scheme"],
            (r["total_shots_budget"], r["shots_per_eval"]))


def grab(mol, opt, sch, bud, field="gap_best_mha"):
    v = [r[field] for r in ok if r["molecule"] == mol and r["optimizer"] == opt
         and r["scheme"] == sch and (r["total_shots_budget"], r["shots_per_eval"]) == bud]
    return np.array(v)


for mol in sorted(set(r["molecule"] for r in ok)):
    print("=" * 116)
    print("%s  --  median gap over 10 seeds, mHa (exact energy at the parameters the "
          "optimiser hands back)" % mol)
    print("=" * 116)
    for bud in sorted(BUD, key=lambda b: BUD[b]):
        lab = BUD[bud]
        print("\n  budget %s" % lab)
        print("  %-11s %11s %11s %11s %11s | %-28s" %
              ("optimizer", "uniform", "weighted", "neyman", "EXACT", "noise cost (uniform - exact)"))
        print("  " + "-" * 112)
        for opt in OPTS:
            cells, med = [], {}
            for s in SCH:
                v = grab(mol, opt, s, bud)
                med[s] = np.median(v) if v.size else float("nan")
                cells.append("%11.2f" % med[s] if v.size else "%11s" % "-")
            gap = med["uniform"] - med["exact"]
            ney = med["neyman"] - med["exact"]
            note = "%+8.2f   neyman %+8.2f" % (gap, ney)
            print("  %-11s %s | %s" % (opt, " ".join(cells), note))
    print()

print("=" * 116)
print("THE DECISIVE COMPARISON -- neyman vs uniform, at identical total shots")
print("=" * 116)
print("%-6s %-11s %-24s %10s %10s %10s %9s" %
      ("mol", "optimizer", "budget", "uniform", "neyman", "difference", "shots ok?"))
print("-" * 116)
wins = losses = ties = 0
for mol in sorted(set(r["molecule"] for r in ok)):
    for bud in sorted(BUD, key=lambda b: BUD[b]):
        for opt in OPTS:
            u = grab(mol, opt, "uniform", bud)
            n = grab(mol, opt, "neyman", bud)
            if not u.size or not n.size:
                continue
            su = grab(mol, opt, "uniform", bud, "shots_consumed")
            sn = grab(mol, opt, "neyman", bud, "shots_consumed")
            fair = "yes" if abs(np.median(su) - np.median(sn)) / max(np.median(su), 1) < 0.02 else "NO"
            dm = np.median(u) - np.median(n)
            # paired over seeds, so per-seed sign is meaningful
            if dm > 1.0:
                wins += 1
            elif dm < -1.0:
                losses += 1
            else:
                ties += 1
            print("%-6s %-11s %-24s %10.2f %10.2f %+10.2f %9s"
                  % (mol, opt, BUD[bud], np.median(u), np.median(n), dm, fair))
print("-" * 116)
print("  neyman better by >1 mHa: %d   worse by >1 mHa: %d   within 1 mHa: %d"
      % (wins, losses, ties))

print()
print("=" * 116)
print("IS NOISE THE BINDING CONSTRAINT?  noisy run vs its OWN exact control, same eval count")
print("=" * 116)
rows = []
for mol in sorted(set(r["molecule"] for r in ok)):
    for bud in sorted(BUD, key=lambda b: BUD[b]):
        for opt in OPTS:
            e = grab(mol, opt, "exact", bud)
            u = grab(mol, opt, "uniform", bud)
            if not e.size or not u.size:
                continue
            rows.append((np.median(u) - np.median(e), mol, opt, BUD[bud],
                         np.median(e), np.median(u)))
rows.sort(key=lambda r: -abs(r[0]))
print("%-6s %-11s %-24s %11s %11s %11s" %
      ("mol", "optimizer", "budget", "exact", "uniform", "noise cost"))
print("-" * 116)
for r in rows[:14]:
    print("%-6s %-11s %-24s %11.2f %11.2f %+11.2f" % (r[1], r[2], r[3], r[4], r[5], r[0]))
print("-" * 116)
allc = np.array([r[0] for r in rows])
print("  median noise cost across all %d cells: %+.2f mHa" % (len(allc), np.median(allc)))
print("  cells where noise costs more than 10 mHa: %d/%d" % ((allc > 10).sum(), len(allc)))
print("  cells where noise costs more than 1 mHa:  %d/%d" % ((allc > 1).sum(), len(allc)))

print()
print("=" * 116)
print("SHOT ACCOUNTING -- actually consumed, not assumed")
print("=" * 116)
for bud in sorted(BUD, key=lambda b: BUD[b]):
    for s in ["uniform", "weighted", "neyman"]:
        v = np.array([r["shots_consumed"] for r in ok
                      if (r["total_shots_budget"], r["shots_per_eval"]) == bud and r["scheme"] == s])
        if v.size:
            print("  %-24s %-9s median %12d   max %12d   (budget %d)"
                  % (BUD[bud], s, np.median(v), v.max(), bud[0]))
