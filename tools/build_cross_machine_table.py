#!/usr/bin/env python3
"""Collect verification-sweep records from several machines into one measured table.

    python tools/build_cross_machine_table.py \
        --sweep cluster=~/sweep_runs/vsweep --sweep workstation=~/qencode_runs/local_sweep

Why this exists. Until 2026-09-07 the robustness of an entry across environments was
recorded by hand, from a handful of runs against a *drifted package stack*. The sweep of
that day measured a different and sharper axis: the SAME pinned stack on two different
machines. Every entry reproduced bit-for-bit on the machine that generated it and moved
on the other one, by between 1e-16 and 8e-3 Ha, which cost two entries their
certification. That is not something to keep in a hand-written dict.

An entry is classified from what was measured, never from the optimiser rule:

    fragile    on some machine it does not certify (regenerated gap >= 0.01 Ha)
    marginal   certifies everywhere measured, but somewhere moved at least as far as its
               own margin -- it passed because the movement happened to shrink the gap,
               and the opposite sign would have failed it
    robust     certifies everywhere measured, and moved less than its margin everywhere
    unmeasured no verification on a machine other than the one that generated it

A verification whose energy movement is exactly zero is same-machine: bit-identical
reproduction only happens on the generating machine, so such a run says nothing about
robustness and is recorded but not counted.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DB = REPO / "releases" / "v4" / "db"
OUT = REPO / "experiments" / "cross_machine" / "measurements.json"
THRESHOLD_HA = 0.01

# Filled from /proc/cpuinfo, ldd and /etc/os-release on each machine, 2026-09-07.
MACHINES = {
    "workstation": {
        "cpu": "AMD Ryzen Threadripper 2990WX (32-core)",
        "vector_isa": ["fma", "avx2"],
        "libc": "glibc 2.39",
        "os": "Ubuntu 24.04.3 LTS (WSL2)",
    },
    "cluster": {
        "cpu": "Intel Xeon Silver 4316 @ 2.30GHz",
        "vector_isa": ["fma", "avx2", "avx512f"],
        "libc": "glibc 2.34",
        "os": "AlmaLinux 9.3",
        "note": "Dell R650xs, Server1 of four, reached on port 2211",
    },
}


def classify(entry_id, published_gap, certified, verifications):
    """Robustness is a claim about a CERTIFIED entry surviving a change of machine.

    A research-tier entry never claimed to certify, so "fragile" would be meaningless for
    it: it is reported as `research` however far its energy moves.
    """
    margin = (THRESHOLD_HA - published_gap) if certified else None
    other = [v for v in verifications if not v["same_machine"]]
    if not certified:
        return "research", None
    if not other:
        return "unmeasured", margin
    if any(v["certifies"] is False for v in other):
        return "fragile", margin
    if margin and any((v["energy_moved_ha"] or 0) >= margin for v in other):
        return "marginal", margin
    return "robust", margin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="append", required=True,
                    metavar="LABEL=DIR", help="sweep record directory, one per machine")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    published = {}
    for f in DB.glob("*.json"):
        e = json.loads(f.read_text())
        published[e["entry_id"]] = e

    entries = {eid: {"file": None, "published_gap_ha": None, "certified": None,
                     "verifications": []} for eid in published}
    for spec in a.sweep:
        label, _, d = spec.partition("=")
        d = os.path.expanduser(d)
        n = 0
        for f in sorted(glob.glob(os.path.join(d, "records", "*.json"))):
            r = json.loads(Path(f).read_text())
            eid = r["entry_id"]
            if eid not in entries:
                continue
            dE = r.get("energy_diff_ha")
            gap = r.get("regenerated_gap_ha")
            entries[eid]["verifications"].append({
                "machine": label,
                "verdict": r["verdict"],
                "energy_moved_ha": dE,
                "regenerated_gap_ha": gap,
                "certifies": (gap < THRESHOLD_HA) if gap is not None else None,
                "same_machine": dE == 0.0,
                "seconds": r.get("seconds"),
            })
            n += 1
        print("  %-12s %3d records from %s" % (label, n, d))

    n_class = {}
    for eid, rec in entries.items():
        e = published[eid]
        rec["file"] = "%s.json" % eid
        rec["molecule"] = e["problem"]["name"]
        rec["mapping"] = e["encoding"]["mapping"]
        rec["ansatz_type"] = e["encoding"]["ansatz_type"]
        rec["optimizer"] = (e.get("run_config") or {}).get("optimizer")
        rec["published_gap_ha"] = e["results"]["quality"]["abs_vqe_exact_gap"]
        rec["certified"] = e["trust"]["level"] == "certified"
        cls, margin = classify(eid, rec["published_gap_ha"], rec["certified"],
                               rec["verifications"])
        rec["margin_ha"] = margin
        rec["classification"] = cls
        rec["max_energy_moved_ha"] = max(
            [v["energy_moved_ha"] or 0 for v in rec["verifications"] if not v["same_machine"]] or [None])
        n_class[cls] = n_class.get(cls, 0) + 1

    out = {
        "schema": "qencode-cross-machine/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "threshold_ha": THRESHOLD_HA,
        "machines": MACHINES,
        "how_classified": {
            "fragile": "does not certify on some machine other than its generating one",
            "marginal": "certifies everywhere, but moved at least its own margin somewhere",
            "robust": "certifies everywhere and moved less than its margin everywhere",
            "unmeasured": "only verified on the machine that generated it",
            "research": "research-tier entry; it never claimed certification, so robustness does not apply",
        },
        "counts": n_class,
        "entries": entries,
    }
    p = Path(os.path.expanduser(a.out))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1) + "\n")
    print("\n  %d entries -> %s" % (len(entries), p))
    for k in sorted(n_class):
        print("    %-11s %d" % (k, n_class[k]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
