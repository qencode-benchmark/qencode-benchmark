#!/usr/bin/env python
"""Early-stopping control: is the budget-B Neyman benefit just a termination artefact?

If refusing to stop recovers most of the gain, the practitioner-facing fix is free -- set
the tolerances to zero and restart on stall -- and "Neyman rescues optimisation" has to be
demoted to "Neyman helps a little on top of a fix that costs nothing".

The comparison that decides it:
    uniform + refuse-to-stop   vs   neyman (plain)
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

BASES = ["COBYLA", "LBFGSB", "LBFGSB_ps"]
SCH = ["uniform", "weighted", "neyman", "exact"]


def get(mol, opt, sch, field="gap_best_mha"):
    return np.array([r[field] for r in ok
                     if r["molecule"] == mol and r["optimizer"] == opt and r["scheme"] == sch])


def med(mol, opt, sch, field="gap_best_mha"):
    v = get(mol, opt, sch, field)
    return np.median(v) if v.size else float("nan")


for mol in sorted(set(r["molecule"] for r in ok)):
    print("=" * 118)
    print("%s   median gap over 10 seeds, mHa   (budget 1e8 shots, 1e5 per eval, cap 1000)" % mol)
    print("=" * 118)
    print("%-12s %-16s %10s %10s %10s %10s | %8s %8s"
          % ("optimizer", "stopping", "uniform", "weighted", "neyman", "exact", "evals", "shots"))
    print("-" * 118)
    for b in BASES:
        for opt, lab in ((b, "default"), (b + "_r", "refuse to stop")):
            row = [med(mol, opt, s) for s in SCH]
            ev = med(mol, opt, "uniform", "evaluations")
            sh = med(mol, opt, "uniform", "shots_consumed")
            if np.isnan(row[0]):
                continue
            print("%-12s %-16s %10.2f %10.2f %10.2f %10.2f | %8.0f %8.1fM"
                  % (b, lab, row[0], row[1], row[2], row[3], ev, sh / 1e6))
        print("-" * 118)
    print()

print("=" * 118)
print("THE 2x2 -- allocation quality x permission to keep going")
print("  Neither fix substitutes for the other. Refusing to stop lets an optimiser spend")
print("  its budget; whether spending it helps depends on the signal being clean enough")
print("  to make progress with.")
print("=" * 118)
print("%-5s %-12s | %11s %11s | %11s %11s | %s"
      % ("mol", "optimizer", "uni/default", "uni/nostop", "ney/default", "ney/nostop", "what it takes"))
print("-" * 118)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        a = med(mol, b, "uniform"); bb = med(mol, b + "_r", "uniform")
        c = med(mol, b, "neyman");  dd = med(mol, b + "_r", "neyman")
        if any(np.isnan(x) for x in (a, bb, c, dd)):
            continue
        best = min(a, bb, c, dd)
        if best > 0.5 * a:
            v = "nothing helps"
        elif dd <= min(bb, c) - 1:
            v = "BOTH needed"
        elif bb <= c - 1:
            v = "stopping fix alone"
        elif c <= bb - 1:
            v = "allocation alone"
        else:
            v = "either works"
        print("%-5s %-12s | %11.2f %11.2f | %11.2f %11.2f | %s"
              % (mol, b, a, bb, c, dd, v))
print("-" * 118)
print("  uni/default = plain uniform allocation, optimiser stops when it wants")
print("  nostop      = tolerances zeroed and restarted on stall until the budget is gone")

print()
print("=" * 118)
print("BEST ACHIEVABLE PER OPTIMISER -- is uniform+stop or neyman+stop the better recipe?")
print("=" * 118)
print("%-5s %-12s | %-22s %-22s | %s" % ("mol", "optimizer", "best without pilot", "best with pilot", "pilot worth it?"))
print("-" * 118)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        nop = min(med(mol, b, "uniform"), med(mol, b + "_r", "uniform"),
                  med(mol, b, "weighted"), med(mol, b + "_r", "weighted"))
        wp = min(med(mol, b, "neyman"), med(mol, b + "_r", "neyman"))
        if np.isnan(nop) or np.isnan(wp):
            continue
        print("%-5s %-12s | %-22.2f %-22.2f | %s"
              % (mol, b, nop, wp, "yes, %.2f mHa better" % (nop - wp) if wp < nop - 1
                 else "no" if wp > nop + 1 else "tie"))

print()
print("=" * 118)
print("DID THE CONTROL ACTUALLY DO ANYTHING?  evaluations spent of the 1000 cap")
print("=" * 118)
print("%-5s %-12s %-16s %8s %8s %8s %8s %9s"
      % ("mol", "optimizer", "stopping", "uniform", "weighted", "neyman", "exact", "restarts"))
print("-" * 118)
for mol in sorted(set(r["molecule"] for r in ok)):
    for b in BASES:
        for opt, lab in ((b, "default"), (b + "_r", "refuse to stop")):
            row = [med(mol, opt, s, "evaluations") for s in SCH]
            rs = med(mol, opt, "uniform", "restarts")
            if np.isnan(row[0]):
                continue
            print("%-5s %-12s %-16s %8.0f %8.0f %8.0f %8.0f %9.0f"
                  % (mol, b, lab, row[0], row[1], row[2], row[3], rs))
