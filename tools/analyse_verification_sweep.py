#!/usr/bin/env python
"""Summarise the full verifier sweep.

QEncode's central claim is that any published result can be independently rebuilt. Until
the verifier was fixed it could not even re-run the 29 entries storing ansatz_type "hea",
so the database had never been checked end to end. This reports what checking it found,
including anything that failed.

    python analyse_sweep.py <dir>
"""
import json
import glob
import os
import sys
from collections import Counter

d = sys.argv[1] if len(sys.argv) > 1 else "."
recs = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "*.json")))]
if not recs:
    print("no records in", d)
    raise SystemExit(1)

verdicts = Counter(r["verdict"] for r in recs)
total = len(recs)
npass = verdicts.get("PASS", 0)

print("=" * 104)
print("FULL VERIFIER SWEEP — %d entries re-run from a clean checkout, pinned environment,"
      % total)
print("no override flags. Each is a complete VQE re-run compared against the stored energy.")
print("=" * 104)
print()
for v, n in verdicts.most_common():
    print("  %-14s %3d  (%5.1f%%)" % (v, n, 100.0 * n / total))
print()
print("  reproduced: %d of %d  (%.1f%%)" % (npass, total, 100.0 * npass / total))
print()

# what did NOT pass, in full
bad = [r for r in recs if r["verdict"] != "PASS"]
if bad:
    print("=" * 104)
    print("NOT REPRODUCED — every one, with its numbers")
    print("=" * 104)
    print("%-46s %-12s %-11s %12s %10s"
          % ("entry", "verdict", "ansatz", "energy diff", "stored gap"))
    print("-" * 104)
    for r in sorted(bad, key=lambda x: (x["verdict"], x["file"])):
        print("%-46s %-12s %-11s %12s %10s"
              % (r["file"][:46], r["verdict"], (r.get("ansatz_type") or "?")[:11],
                 ("%.2e" % r["energy_diff_ha"]) if r.get("energy_diff_ha") else "-",
                 ("%.2e" % r["stored_gap_ha"]) if r.get("stored_gap_ha") is not None else "-"))
    print()

# breakdowns, so a failure pattern is visible rather than buried
print("=" * 104)
print("BY ANSATZ  (the 'hea' rows are the ones the verifier could not run before a298c51)")
print("=" * 104)
print("%-18s %6s %6s %6s   %s" % ("ansatz_type", "total", "pass", "other", "pass rate"))
print("-" * 104)
for a in sorted({r.get("ansatz_type") or "?" for r in recs}):
    sub = [r for r in recs if (r.get("ansatz_type") or "?") == a]
    p = sum(1 for r in sub if r["verdict"] == "PASS")
    print("%-18s %6d %6d %6d   %5.1f%%"
          % (a, len(sub), p, len(sub) - p, 100.0 * p / len(sub)))

print()
print("=" * 104)
print("BY OPTIMIZER")
print("=" * 104)
for o in sorted({(r.get("optimizer") or "?") for r in recs}):
    sub = [r for r in recs if (r.get("optimizer") or "?") == o]
    p = sum(1 for r in sub if r["verdict"] == "PASS")
    print("  %-44s %3d entries, %3d reproduced  (%5.1f%%)"
          % (o[:44], len(sub), p, 100.0 * p / len(sub)))

print()
print("=" * 104)
print("BY MOLECULE")
print("=" * 104)
mols = sorted({r.get("molecule") or "?" for r in recs})
for m in mols:
    sub = [r for r in recs if (r.get("molecule") or "?") == m]
    p = sum(1 for r in sub if r["verdict"] == "PASS")
    flag = "" if p == len(sub) else "   <-- not all reproduced"
    print("  %-14s %2d entries, %2d reproduced%s" % (m, len(sub), p, flag))

print()
print("=" * 104)
print("COST OF A FULL RE-VERIFICATION")
print("=" * 104)
secs = sorted((r.get("seconds") or 0) for r in recs)
tot = sum(secs)
print("  total compute      %.1f hours across %d entries" % (tot / 3600.0, total))
print("  median entry       %ds" % secs[len(secs) // 2])
print("  slowest entry      %ds (%.1f h)" % (secs[-1], secs[-1] / 3600.0))
slow = sorted(recs, key=lambda r: -(r.get("seconds") or 0))[:5]
print("  slowest five:")
for r in slow:
    print("     %-52s %6ds  %s" % (r["file"][:52], r.get("seconds") or 0, r["verdict"]))
