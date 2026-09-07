#!/usr/bin/env python3
"""Re-verify every published entry, in parallel, and record the outcome.

    python scripts/verification_sweep.py                      # all entries, strict
    python scripts/verification_sweep.py --parallel 20
    python scripts/verification_sweep.py --entries H2 LiH     # substrings of the filename
    python scripts/verification_sweep.py --summarise          # re-read records, no runs

Each entry is regenerated through `scripts/verify_entry.py`, which runs the real pipeline
from the entry's own recorded configuration and compares the energy it gets with the one
the entry stores. In `strict` mode the two must agree to 1e-6 Ha, which is only meaningful
in an environment matching requirements-v4.txt -- both the workstation and the cluster
venv do (verified bit-for-bit, identical content hashes). In `certification` mode the test
is instead that the regenerated gap still clears the 0.01 Ha threshold, which is the right
question on a machine whose stack has drifted.

The previous sweep, on 2026-08-27, was driven by an ad-hoc shell loop that left only a log.
This exists so the sweep is a tool with records, provenance and a resumable run, and so
that the sweep after a suite change is a command rather than an improvisation.

Writes, under --out-dir:
    records/<entry_id>.json   one per entry, matching the 2026-08-27 record schema
    sweep.log                 human-readable, in completion order
    summary.json              provenance + counts + the full table
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO / "releases" / "v4" / "db"
DEFAULT_OUT = REPO / "experiments" / "verification_sweep"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _run(cmd, timeout, cwd=REPO):
    env = dict(os.environ, QENCODE_REPO=str(REPO))
    try:
        p = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, ANSI.sub("", p.stdout + p.stderr)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ss" % timeout


def _git(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=str(REPO),
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def verify_one(path: Path, mode: str, timeout: int, out_dir: Path) -> dict:
    entry = json.loads(path.read_text())
    rec = {
        "entry_id": entry["entry_id"],
        "file": path.name,
        "molecule": entry["problem"]["name"],
        "mapping": entry["encoding"]["mapping"],
        "ansatz_type": entry["encoding"]["ansatz_type"],
        "optimizer": (entry.get("run_config") or {}).get("optimizer"),
        "trust": entry["trust"]["level"],
        "stored_gap_ha": entry["results"]["quality"]["abs_vqe_exact_gap"],
        "mode": mode,
    }
    t0 = time.time()
    rc, out = _run([sys.executable, str(REPO / "scripts" / "verify_entry.py"),
                    str(path), "--mode", mode], timeout)
    rec["seconds"] = round(time.time() - t0, 1)
    rec["returncode"] = rc

    m = re.search(r"\|ΔE\|:\s*([0-9.eE+-]+)\s*Ha", out)
    rec["energy_diff_ha"] = float(m.group(1)) if m else None
    m = re.search(r"Regenerated gap:\s*([0-9.eE+-]+)\s*Ha", out)
    rec["regenerated_gap_ha"] = float(m.group(1)) if m else None
    if "[PASS]" in out:
        rec["verdict"] = "PASS"
    elif "[FAIL]" in out:
        rec["verdict"] = "FAIL"
    else:
        rec["verdict"] = "ERROR"
    if rec["verdict"] != "PASS":
        tail = [l for l in out.splitlines() if l.strip()][-6:]
        rec["reason"] = "\n".join(tail)[:1500]

    (out_dir / "records").mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "records" / (rec["entry_id"] + ".json.tmp")
    tmp.write_text(json.dumps(rec, indent=1) + "\n")
    tmp.replace(out_dir / "records" / (rec["entry_id"] + ".json"))
    return rec


def line(rec):
    return "  %-7s %-58s %7.0fs  dE=%-10s gap=%s" % (
        rec["verdict"], rec["entry_id"][:58], rec["seconds"],
        ("%.2e" % rec["energy_diff_ha"]) if rec["energy_diff_ha"] is not None else "-",
        ("%.3e" % rec["regenerated_gap_ha"]) if rec["regenerated_gap_ha"] is not None else "-")


def summarise(out_dir: Path, meta: dict | None = None):
    recs = [json.loads(p.read_text()) for p in sorted((out_dir / "records").glob("*.json"))]
    counts = {}
    for r in recs:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    moved = [r for r in recs if (r.get("energy_diff_ha") or 0) > 0]
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": meta or {},
        "counts": counts,
        "n_entries": len(recs),
        "max_energy_movement_ha": max([r.get("energy_diff_ha") or 0 for r in recs] or [0]),
        "entries_that_moved": len(moved),
        "records": sorted(recs, key=lambda r: (r["verdict"] != "PASS", -r["seconds"])),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print("\n  %d entries: %s" % (len(recs), ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items()))))
    print("  largest energy movement: %.3e Ha across %d entries that moved at all"
          % (summary["max_energy_movement_ha"], len(moved)))
    for r in recs:
        if r["verdict"] != "PASS":
            print("  %s %s\n    %s" % (r["verdict"], r["entry_id"], (r.get("reason") or "").splitlines()[:1]))
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db-dir", default=str(DEFAULT_DB))
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--mode", default="strict", choices=["strict", "certification"])
    ap.add_argument("--parallel", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=21600, help="seconds per entry")
    ap.add_argument("--entries", nargs="*", default=[], help="filename substrings")
    ap.add_argument("--force", action="store_true", help="re-verify entries that already have a record")
    ap.add_argument("--summarise", action="store_true")
    a = ap.parse_args()

    out_dir = Path(a.out_dir)
    if a.summarise:
        summarise(out_dir)
        return 0

    files = sorted(Path(a.db_dir).glob("*.json"))
    if a.entries:
        files = [f for f in files if any(s in f.name for s in a.entries)]
    done = {p.stem for p in (out_dir / "records").glob("*.json")} if not a.force else set()
    todo = [f for f in files if json.loads(f.read_text())["entry_id"] not in done]

    meta = {
        "host": platform.node(),
        "python": platform.python_version(),
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_dirty_files": len([l for l in (_git("status", "--porcelain") or "").splitlines()
                                if l and not l.startswith("??")]),
        "mode": a.mode,
        "parallel": a.parallel,
        "timeout_s": a.timeout,
        "started_utc": datetime.now(timezone.utc).isoformat(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    log = open(out_dir / "sweep.log", "a")
    header = ("=== verification sweep ===\n%s\nhost: %s  commit: %s  dirty: %d\n"
              "entries: %d (%d to run)  mode: %s  parallel: %d  timeout: %ss\n"
              % (meta["started_utc"], meta["host"], meta["git_commit"], meta["git_dirty_files"],
                 len(files), len(todo), a.mode, a.parallel, a.timeout))
    print(header)
    log.write("\n" + header)
    log.flush()

    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.parallel) as ex:
        futs = {ex.submit(verify_one, f, a.mode, a.timeout, out_dir): f for f in todo}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            rec = fut.result()
            s = "[%2d/%2d]%s" % (i, len(todo), line(rec))
            print(s, flush=True)
            log.write(s + "\n")
            log.flush()

    meta["finished_utc"] = datetime.now(timezone.utc).isoformat()
    meta["wall_seconds"] = round(time.time() - t0, 1)
    summary = summarise(out_dir, meta)
    log.write("wall %.0fs; %s\n" % (meta["wall_seconds"],
                                    ", ".join("%s %d" % kv for kv in sorted(summary["counts"].items()))))
    log.close()
    return 0 if summary["counts"].get("PASS", 0) == summary["n_entries"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
