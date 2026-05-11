#!/usr/bin/env python3
"""
export_leaderboard_v3.py — Build leaderboard CSVs from v3 entry db
=====================================================================
Reads all JSON entries in releases/v3/db/, ranks them, and writes:
  website/public/data/leaderboard_accuracy.csv
  website/public/data/leaderboard_hardware_cost.csv
  website/public/data/leaderboard_balanced.csv
  website/public/data/leaderboard_research.csv
  website/public/data/leaderboard_metadata.json

Run from repo root (Windows or Ubuntu):
  python scripts/export_leaderboard_v3.py
  python scripts/export_leaderboard_v3.py --dry-run

Rankings:
  Accuracy  : rank certified entries by gap ASC (best accuracy first)
  Cost      : rank certified entries (with circuit metrics) by 2Q gates ASC, then depth ASC
  Balanced  : rank-based combined score:
                balanced_score = 0.5*(gap_rank/(N-1)) + 0.5*(cost_rank/(N-1))  ∈ [0,1]
              Lower is better. Requires circuit metrics.
  Research  : validated entries (gap ≥ 0.01 Ha or trust=validated), rank by gap ASC.

beats_classical = results.quality.beats_classical (True if |VQE gap| < |CCSD(T) correlation|)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

REPO            = Path(__file__).resolve().parent.parent
DEFAULT_DB_DIR  = REPO / "releases" / "v3" / "db"
OUTPUT_DIR      = REPO / "website" / "public" / "data"

# Overridden by --suite-version CLI arg
DEFAULT_SUITE_VERSION  = "3"
LEADERBOARD_RULES      = "1"
GAP_THRESHOLD          = 0.01   # Hartree — certified threshold


# ── Mapping / ansatz normalisation (entry values → website keys) ──────────────

MAPPING_MAP = {
    "jordan_wigner":  "jordan_wigner",
    "bravyi_kitaev":  "bravyi_kitaev",
    "parity":         "parity",
}

ANSATZ_MAP = {
    "hea":            "hardware_efficient",
    "uccsd":          "UCCSD",
    "uccsd_tapered":  "UCCSD",
    "hardware_efficient": "hardware_efficient",
}


# ── Load entries ──────────────────────────────────────────────────────────────

def load_entries(db_dir: Path) -> list[dict]:
    """Load all v3/v3.1 JSON entries from db_dir."""
    entries = []
    for p in sorted(db_dir.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            try:
                entries.append(json.load(f))
            except json.JSONDecodeError as ex:
                print(f"  [WARN] Could not parse {p.name}: {ex}")
    return entries


def _num(v):
    """Return float or None."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── Build flat row from entry ─────────────────────────────────────────────────

def entry_to_row(entry: dict) -> dict | None:
    """Extract a flat row dict from a v3 entry. Returns None if data is incomplete."""
    try:
        mol     = entry["problem"]["name"]
        mapping = MAPPING_MAP.get(entry["encoding"]["mapping"], entry["encoding"]["mapping"])
        ansatz  = ANSATZ_MAP.get(entry["encoding"]["ansatz_type"], entry["encoding"]["ansatz_type"])
        trust   = entry.get("trust", {}).get("level", "pending")

        qual    = entry.get("results", {}).get("quality", {})
        gap     = _num(qual.get("abs_vqe_exact_gap"))
        beats   = qual.get("beats_classical")

        # Classical comparison — DARPA Phase 7
        cc           = entry.get("results", {}).get("classical_comparison", {})
        ccsd_t_corr  = _num(cc.get("ccsd_t_correlation"))   # |CCSD(T) correlation energy| Ha
        vqe_energy   = _num(entry.get("results", {}).get("vqe", {}).get("best_energy_hartree"))
        casci_energy = _num(entry.get("results", {}).get("reference", {}).get("casci_ground_energy_hartree"))
        hf_energy    = _num(cc.get("hf_energy_hartree"))

        cs      = entry.get("circuit_stats", {})
        depth   = cs.get("ansatz_depth")
        twoq    = cs.get("ansatz_num_2q_gates")
        n_params= cs.get("ansatz_num_parameters")

        # Validated entries with no gap recorded (shouldn't happen, but guard)
        if gap is None:
            return None

        return {
            "molecule":         mol,
            "mapping":          mapping,
            "ansatz":           ansatz,
            "gap":              gap,
            "depth":            depth,
            "twoq":             twoq,
            "n_params":         n_params,
            "trust":            trust,
            "beats_classical":  beats,
            "baseline":         True,   # all v3 entries are QEncode baseline runs
            # Classical comparison (Phase 7 — DARPA alignment)
            "ccsd_t_correlation": ccsd_t_corr,
            "vqe_energy":         vqe_energy,
            "casci_energy":       casci_energy,
            "hf_energy":          hf_energy,
        }
    except (KeyError, TypeError) as ex:
        print(f"  [WARN] Skipping entry {entry.get('entry_id','?')}: {ex}")
        return None


# ── Ranking helpers ────────────────────────────────────────────────────────────

def _rank_rows(rows: list[dict], key_fn, ascending=True) -> list[dict]:
    """Assign 1-indexed rank, handling ties (same rank for equal values)."""
    rows = list(rows)
    rows.sort(key=lambda r: (key_fn(r) is None, key_fn(r) if key_fn(r) is not None else 0),
              reverse=not ascending)
    rank = 1
    prev_val = None
    prev_rank = 1
    for i, r in enumerate(rows):
        val = key_fn(r)
        if i == 0:
            r["rank"] = 1
            prev_val  = val
            prev_rank = 1
        else:
            if val == prev_val:
                r["rank"] = prev_rank
            else:
                r["rank"]  = i + 1
                prev_rank  = i + 1
                prev_val   = val
    return rows


def _balanced_score(row, gap_rank_norm, cost_rank_norm) -> float:
    """Combined rank-based balanced score in [0, 1]. Lower is better."""
    return 0.5 * gap_rank_norm + 0.5 * cost_rank_norm


# ── CSV writers ───────────────────────────────────────────────────────────────

def _write_csv(path: Path, fieldnames: list[str], rows: list[dict], dry_run: bool):
    if dry_run:
        print(f"  [DRY-RUN] Would write {len(rows)} rows -> {path.name}")
        for r in rows[:3]:
            print(f"    {r}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  [OK] {path.name}  ({len(rows)} rows)")


# ── Main export ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Build leaderboard CSVs from v3/v3.1 entry db"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written, don't write files")
    parser.add_argument("--db-dir", default=str(DEFAULT_DB_DIR),
                        help="Path to db directory containing JSON entry files "
                             "(default: releases/v3/db). "
                             "For v3.1 use: releases/v3.1/db")
    parser.add_argument("--suite-version", default=DEFAULT_SUITE_VERSION,
                        help="Suite version string to embed in metadata (e.g. '3', '3.1')")
    args = parser.parse_args()

    db_dir = Path(args.db_dir)
    suite_version = args.suite_version

    print(f"\n{'='*65}")
    print(f"  QEncode Leaderboard Export  (Suite v{suite_version})")
    print(f"  DB:     {db_dir}")
    print(f"  Output: {OUTPUT_DIR}")
    if args.dry_run:
        print("  MODE: DRY-RUN")
    print(f"{'='*65}\n")

    # ── 1. Load all entries ───────────────────────────────────────────────────
    entries = load_entries(db_dir)
    print(f"  Loaded {len(entries)} entries from {db_dir.name}/\n")

    rows = [r for e in entries if (r := entry_to_row(e)) is not None]
    print(f"  Valid rows: {len(rows)}")

    # ── 2. Partition: certified vs validated ──────────────────────────────────
    certified = [r for r in rows if r["trust"] == "certified"]
    validated = [r for r in rows if r["trust"] != "certified"]
    print(f"  Certified: {len(certified)}  |  Validated (research): {len(validated)}\n")

    # ── 3. Accuracy leaderboard ───────────────────────────────────────────────
    acc_rows = _rank_rows(certified, key_fn=lambda r: r["gap"], ascending=True)
    acc_csv  = [
        {
            "rank":               r["rank"],
            "molecule":           r["molecule"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "vqe_energy":         r["vqe_energy"],
            "casci_energy":       r["casci_energy"],
            "hf_energy":          r["hf_energy"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
        }
        for r in acc_rows
    ]

    # ── 4. Hardware cost leaderboard ──────────────────────────────────────────
    # Only entries with actual circuit metrics (2Q gates and depth populated)
    cost_eligible = [r for r in certified if r["twoq"] is not None and r["depth"] is not None]
    cost_rows = _rank_rows(
        cost_eligible,
        key_fn=lambda r: (r["twoq"], r["depth"]),
        ascending=True,
    )
    cost_csv = [
        {
            "rank":               r["rank"],
            "molecule":           r["molecule"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "depth":              r["depth"],
            "2q_gates":           r["twoq"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
        }
        for r in cost_rows
    ]

    # ── 5. Balanced leaderboard ───────────────────────────────────────────────
    # Uses rank-based balanced score on entries with circuit metrics
    balanced_eligible = cost_eligible   # same subset as cost
    N = len(balanced_eligible)

    if N > 1:
        # Sort by gap → get gap rank index (0-based)
        gap_sorted  = sorted(balanced_eligible, key=lambda r: r["gap"])
        cost_sorted = sorted(balanced_eligible, key=lambda r: (r["twoq"], r["depth"]))

        gap_rank_map  = {id(r): i for i, r in enumerate(gap_sorted)}
        cost_rank_map = {id(r): i for i, r in enumerate(cost_sorted)}

        for r in balanced_eligible:
            gr = gap_rank_map[id(r)]  / (N - 1)
            cr = cost_rank_map[id(r)] / (N - 1)
            r["balanced_score"] = round(0.5 * gr + 0.5 * cr, 6)
    else:
        for r in balanced_eligible:
            r["balanced_score"] = 0.0

    balanced_rows = _rank_rows(balanced_eligible,
                               key_fn=lambda r: r["balanced_score"],
                               ascending=True)
    balanced_csv = [
        {
            "rank":               r["rank"],
            "molecule":           r["molecule"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "depth":              r["depth"],
            "2q_gates":           r["twoq"],
            "balanced_score":     r["balanced_score"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
        }
        for r in balanced_rows
    ]

    # ── 6. Research leaderboard ───────────────────────────────────────────────
    res_rows = _rank_rows(validated, key_fn=lambda r: r["gap"], ascending=True)
    research_csv = [
        {
            "rank":               r["rank"],
            "molecule":           r["molecule"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "vqe_energy":         r["vqe_energy"],
            "casci_energy":       r["casci_energy"],
            "hf_energy":          r["hf_energy"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
        }
        for r in res_rows
    ]

    # ── 7. Metadata ───────────────────────────────────────────────────────────
    beats_count = sum(1 for r in certified if r["beats_classical"] is True)
    metadata = {
        "suite_version":      suite_version,
        "leaderboard_rules":  LEADERBOARD_RULES,
        "generation_date":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "entries_included":   len(certified),
        "trust_filter":       "certified_only",
        "beats_classical_count": beats_count,
        "validated_count":    len(validated),
    }

    # ── 8. Summary ────────────────────────────────────────────────────────────
    print(f"  Accuracy:  {len(acc_csv):3} entries")
    print(f"  Cost:      {len(cost_csv):3} entries")
    print(f"  Balanced:  {len(balanced_csv):3} entries")
    print(f"  Research:  {len(research_csv):3} entries")
    print(f"  Beats Classical: {beats_count}/{len(certified)} certified\n")

    # Print top-5 balanced for preview
    print("  Top 5 Balanced:")
    for r in balanced_csv[:5]:
        print(f"    #{r['rank']}  {r['molecule']:4} {r['mapping'][:3].upper()} {r['ansatz'][:3].upper()}"
              f"  gap={r['gap']:.2e}  2q={r['2q_gates']}  score={r['balanced_score']:.4f}"
              f"  beats_classical={r['beats_classical']}")
    print()

    # ── 9. Write files ────────────────────────────────────────────────────────
    _write_csv(
        OUTPUT_DIR / "leaderboard_accuracy.csv",
        ["rank","molecule","mapping","ansatz","gap","ccsd_t_correlation","vqe_energy","casci_energy","hf_energy","baseline","beats_classical"],
        acc_csv, args.dry_run,
    )
    _write_csv(
        OUTPUT_DIR / "leaderboard_hardware_cost.csv",
        ["rank","molecule","mapping","ansatz","gap","depth","2q_gates","ccsd_t_correlation","baseline","beats_classical"],
        cost_csv, args.dry_run,
    )
    _write_csv(
        OUTPUT_DIR / "leaderboard_balanced.csv",
        ["rank","molecule","mapping","ansatz","gap","depth","2q_gates","balanced_score","ccsd_t_correlation","baseline","beats_classical"],
        balanced_csv, args.dry_run,
    )
    _write_csv(
        OUTPUT_DIR / "leaderboard_research.csv",
        ["rank","molecule","mapping","ansatz","gap","ccsd_t_correlation","vqe_energy","casci_energy","hf_energy","baseline","beats_classical"],
        research_csv, args.dry_run,
    )

    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        meta_path = OUTPUT_DIR / "leaderboard_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"  [OK] leaderboard_metadata.json")
    else:
        print(f"  [DRY-RUN] Would write leaderboard_metadata.json: {metadata}")

    print(f"\n{'='*65}")
    print(f"  DONE - leaderboard exported to {OUTPUT_DIR}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
