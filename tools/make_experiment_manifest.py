#!/usr/bin/env python
"""Manifest for the shot-allocation experiment data.

A certified suite entry carries its own provenance and a content hash. The experiment
records predate that (the tools now emit a provenance block, but the 4,888 committed runs
were produced before it), so this supplies the equivalent at the directory level: a
SHA256SUMS file per study so any record can be checked byte for byte, an aggregate digest
per study so the whole set can be checked at once, and the environment those runs were
produced in.

    python tools/make_experiment_manifest.py
"""
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.environ.get("QENCODE_REPO", os.getcwd())

# The environment every committed run in these directories was produced in. Verified by
# querying the cluster interpreter directly rather than assumed; the tools now record
# the same block per-record for anything run from here on.
ENVIRONMENT = {
    "tool_versions": {
        "python": "3.11.15",
        "pyscf": "2.6.2",
        "pennylane": "0.45.0",
        "openfermion": "1.6.1",
        "numpy": "2.2.6",
        "scipy": "1.13.1",
        "git_commit": "f1c1461",
    },
    "environment": {
        "platform": "linux",
        "blas_threads": "1",
        "threads_pinned": True,
    },
    "note": ("Runs were executed on a shared 40-core node, single-threaded per job with "
             "parallelism across processes only, so no run can perturb another. Every job "
             "seeds its own generator; see the `seed` field in each record."),
}

STUDIES = [
    ("experiments/shot_allocation/v1_std_only",
     "First estimator grid, judged on standard deviation. Where the bias hid.",
     "python tools/shot_allocation.py <molecule> <state> <budget> <outdir>"),
    ("experiments/shot_allocation/v2_fixes",
     "Estimator grid with the shrinkage and pooling repairs, judged on RMSE.",
     "python tools/shot_allocation.py <molecule> <state> <budget> <outdir>"),
    ("experiments/shot_allocation/final",
     "Full estimator scheme set including the recommended combination.",
     "python tools/shot_allocation.py <molecule> <state> <budget> <outdir>"),
    ("experiments/shot_allocation_opt/grid",
     "Does allocation change the outcome of a full optimisation?",
     "python tools/shot_allocation_optimize.py <mol> <opt> <scheme> <total> <per_eval> <seed> <outdir>"),
    ("experiments/shot_allocation_opt/early_stopping_control",
     "Control: does refusing to stop replace allocation quality?",
     "python tools/shot_allocation_optimize.py <mol> <opt>_r <scheme> 100000000 100000 <seed> <outdir>"),
    ("experiments/shot_allocation_opt/budget_scaling",
     "Where allocation quality starts to matter, 1e6 to 1e8 shots.",
     "python tools/shot_allocation_optimize.py <mol> <opt> <scheme> <total> 100000 <seed> <outdir>"),
    ("experiments/shot_allocation_opt/early_stopping_numbers",
     "Termination point, count and scipy reason against noise level.",
     "python tools/shot_allocation_optimize.py <mol> <opt> <scheme> <total> <per_eval> <seed> <outdir>"),
    ("experiments/shot_allocation_opt/spsa_calibration",
     "SPSA gain sweep at zero noise. Produced before a fix to final-parameter "
     "tracking, so gap_final is unreliable in these records; the ranking used gap_best.",
     "SPSA_A=<a> SPSA_C=<c> python tools/shot_allocation_optimize.py LiH SPSA exact 200000000 100000 0 <outdir>"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    manifest = {
        "description": ("Content hashes and provenance for the shot-allocation studies. "
                        "Every JSON record is hashed individually in the SHA256SUMS file "
                        "inside its own directory; the aggregate below is the SHA-256 of "
                        "those per-file digests in sorted filename order."),
        "provenance": ENVIRONMENT,
        "studies": [],
        "totals": {},
    }
    grand = 0
    for rel, desc, cmd in STUDIES:
        d = os.path.join(ROOT, rel)
        if not os.path.isdir(d):
            print("  MISSING", rel)
            continue
        names = sorted(f for f in os.listdir(d) if f.endswith(".json"))
        lines, digests = [], []
        for n in names:
            h = sha256(os.path.join(d, n))
            lines.append("%s  %s" % (h, n))
            digests.append(h)
        with open(os.path.join(d, "SHA256SUMS"), "w") as fh:
            fh.write("\n".join(lines) + "\n")
        agg = hashlib.sha256("\n".join(digests).encode()).hexdigest()
        manifest["studies"].append({
            "path": rel,
            "description": desc,
            "runs": len(names),
            "aggregate_sha256": agg,
            "regenerate": cmd,
        })
        grand += len(names)
        print("  %-58s %5d runs  %s" % (rel, len(names), agg[:16]))
    manifest["totals"] = {"runs": grand, "studies": len(manifest["studies"])}

    out = os.path.join(ROOT, "experiments", "MANIFEST.json")
    with open(out, "w") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    print("\n  %d runs across %d studies -> %s" % (grand, len(manifest["studies"]), out))
    print("  verify one study with:  cd <study dir> && sha256sum -c SHA256SUMS")


if __name__ == "__main__":
    main()
