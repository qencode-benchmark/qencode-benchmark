#!/usr/bin/env python3
"""
export_leaderboard_v4.py — Build leaderboard CSVs from v4 entry db
===================================================================
Reads all JSON entries in releases/v4/db/, ranks them, and writes:
  website/public/data/leaderboard_accuracy.csv
  website/public/data/leaderboard_hardware_cost.csv
  website/public/data/leaderboard_balanced.csv
  website/public/data/leaderboard_research.csv
  website/public/data/leaderboard_metadata.json

Differences from export_leaderboard_v3.py:
  - Default db: releases/v4/db/
  - Default suite_version: "4"
  - circuit_stats fields: circuit_depth (was ansatz_depth),
    num_2q_gates (was ansatz_num_2q_gates)
  - Adds 'basis' column to all CSVs (cc-pvdz for all v4 entries)
  - Adds 'orbital_opt' column (hf | casscf)

Run from repo root:
  python scripts/export_leaderboard_v4.py
  python scripts/export_leaderboard_v4.py --dry-run
  python scripts/export_leaderboard_v4.py --db-dir releases/v4/db/

Rankings (same as v3):
  Accuracy  : rank certified entries by gap ASC
  Cost      : rank by 2Q gates ASC, then depth ASC (entries with circuit metrics)
  Balanced  : rank-based combined score (0.5*gap_rank + 0.5*cost_rank)
  Research  : validated entries, rank by gap ASC
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO            = Path(__file__).resolve().parent.parent
DEFAULT_DB_DIR  = REPO / "releases" / "v4" / "db"
OUTPUT_DIR      = REPO / "website" / "public" / "data"

DEFAULT_SUITE_VERSION = "4"
LEADERBOARD_RULES     = "2"
GAP_THRESHOLD         = 0.01   # Hartree — certified threshold
CHEM_ACCURACY         = 1.6e-3 # Hartree — 1 kcal/mol; reported, never a criterion

# Margin, optimiser family, amplification and the measured cross-environment results all
# come from one place so the leaderboard cannot drift from the tool that defines them.
sys.path.insert(0, str(REPO / "tools"))
import certification_margin as _cm  # noqa: E402


def _optimizer_label(s) -> str | None:
    """Short, comma-free label for the row. The raw run_config string can contain
    commas ("L-BFGS-B inner, statevector engine"), which the site's CSV fallback
    parser would split on."""
    s = str(s or "")
    if not s or s == "None":
        return None
    inner = ("COBYLA" if "COBYLA" in s else "L-BFGS-B" if "BFGS" in s
             else "Adam" if "Adam" in s else "SPSA" if "SPSA" in s else s)
    return f"ADAPT-VQE/{inner}" if "ADAPT" in s else inner


def _robustness(entry_id: str) -> str | None:
    """Measured cross-environment outcome, if this entry has been re-run elsewhere."""
    fn = f"{entry_id}.json"
    if fn in _cm.MEASURED_FRAGILE:
        return "fragile"
    if fn in _cm.MEASURED_MARGINAL:
        return "marginal"
    if fn in _cm.MEASURED_ROBUST:
        return "robust"
    return None


# ── Mapping / ansatz normalisation ────────────────────────────────────────────

MAPPING_MAP = {
    "jordan_wigner":  "jordan_wigner",
    "bravyi_kitaev":  "bravyi_kitaev",
    "parity":         "parity",
}

ANSATZ_MAP = {
    "hea":                "hardware_efficient",
    "uccsd":              "UCCSD",
    "uccsd_tapered":      "UCCSD",
    "hardware_efficient": "hardware_efficient",
}


# ── Load entries ──────────────────────────────────────────────────────────────

def load_entries(db_dir: Path) -> list[dict]:
    entries = []
    for p in sorted(db_dir.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            try:
                entries.append(json.load(f))
            except json.JSONDecodeError as ex:
                print(f"  [WARN] Could not parse {p.name}: {ex}")
    return entries


def _num(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ── Build flat row from entry ─────────────────────────────────────────────────

def entry_to_row(entry: dict) -> dict | None:
    """Extract a flat row dict from a v4 entry. Returns None if data is incomplete."""
    try:
        prob    = entry["problem"]
        mol     = prob["name"]
        basis   = prob.get("basis", "cc-pvdz")
        orbital_opt = prob.get("orbital_optimization", "hf")

        mapping = MAPPING_MAP.get(entry["encoding"]["mapping"], entry["encoding"]["mapping"])
        ansatz  = ANSATZ_MAP.get(entry["encoding"]["ansatz_type"], entry["encoding"]["ansatz_type"])
        trust   = entry.get("trust", {}).get("level", "pending")

        qual    = entry.get("results", {}).get("quality", {})
        gap     = _num(qual.get("abs_vqe_exact_gap"))
        beats   = qual.get("beats_classical")

        cc           = entry.get("results", {}).get("classical_comparison", {})
        ccsd_t_corr  = _num(cc.get("ccsd_t_correlation"))
        vqe_energy   = _num(entry.get("results", {}).get("vqe", {}).get("best_energy_hartree"))
        casci_energy = _num(entry.get("results", {}).get("reference", {}).get("casci_ground_energy_hartree"))
        hf_energy    = _num(cc.get("hf_energy_hartree"))

        cs      = entry.get("circuit_stats", {})
        # v4 field names differ from v3:
        #   v4: circuit_depth / num_2q_gates
        #   v3: ansatz_depth  / ansatz_num_2q_gates
        # Support both for defensive compatibility.
        depth   = cs.get("circuit_depth")   or cs.get("ansatz_depth")
        twoq    = cs.get("num_2q_gates")    or cs.get("ansatz_num_2q_gates")
        n_params= cs.get("ansatz_num_parameters")
        # Fault-tolerant resource proxies. Recorded per entry since v4; surfaced on the
        # leaderboard so an entry can be read as a resource estimate, not only an accuracy.
        t_gates      = cs.get("t_gate_estimate")
        non_clifford = cs.get("non_clifford_gate_count")

        if gap is None:
            return None

        # Margin and fragility. An entry certified at 9.98 mHa and one at 0.001 mHa are
        # both "certified"; only one survives being re-run on another machine. The risk
        # is the conjunction of a thin margin and an amplifying (gradient-free optimiser,
        # unstructured ansatz) configuration -- measured, see tools/certification_margin.py.
        entry_id     = entry.get("entry_id", "")
        optimizer    = (entry.get("run_config") or {}).get("optimizer")
        ansatz_raw   = entry["encoding"]["ansatz_type"]
        family       = _cm._optimiser_family(optimizer)
        amplifies    = _cm._amplifies(optimizer, ansatz_raw)
        certified    = gap < GAP_THRESHOLD
        margin       = (GAP_THRESHOLD - gap) if certified else None
        robustness   = _robustness(entry_id)
        thin         = certified and margin < GAP_THRESHOLD * _cm.THIN_MARGIN_FRACTION
        at_risk      = bool(thin and amplifies and robustness is None)

        return {
            "entry_id":           entry_id,
            "optimizer":          _optimizer_label(optimizer),
            "optimiser_family":   family,
            "amplifies":          amplifies,
            "margin":             margin,
            "chem_accurate":      gap < CHEM_ACCURACY,
            "robustness":         robustness,
            "at_risk":            at_risk,
            "molecule":           mol,
            "basis":              basis,
            "orbital_opt":        orbital_opt,
            "mapping":            mapping,
            "ansatz":             ansatz,
            "gap":                gap,
            "depth":              depth,
            "twoq":               twoq,
            "n_params":           n_params,
            "t_gate_estimate":    t_gates,
            "non_clifford_gates": non_clifford,
            "trust":              trust,
            "beats_classical":    beats,
            "baseline":           True,   # all v4 entries are QEncode baseline runs
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
    rows = list(rows)
    rows.sort(key=lambda r: (key_fn(r) is None, key_fn(r) if key_fn(r) is not None else 0),
              reverse=not ascending)
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
        description="Build leaderboard CSVs from v4 entry db"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written, don't write files")
    parser.add_argument("--db-dir", action="append", default=None, dest="db_dirs",
                        help="Path to db directory. Repeat to merge multiple. "
                             "(default: releases/v4/db)")
    parser.add_argument("--suite-version", default=DEFAULT_SUITE_VERSION,
                        help="Suite version string to embed in metadata (default: '4')")
    args = parser.parse_args()

    db_dirs = [Path(d) for d in (args.db_dirs or [str(DEFAULT_DB_DIR)])]
    suite_version = args.suite_version

    print(f"\n{'='*65}")
    print(f"  QEncode Leaderboard Export  (Suite v{suite_version})")
    for d in db_dirs:
        print(f"  DB:     {d}")
    print(f"  Output: {OUTPUT_DIR}")
    if args.dry_run:
        print("  MODE: DRY-RUN")
    print(f"{'='*65}\n")

    # ── 1. Load entries ───────────────────────────────────────────────────────
    entries = []
    for db_dir in db_dirs:
        batch = load_entries(db_dir)
        print(f"  Loaded {len(batch)} entries from {db_dir}/")
        entries.extend(batch)
    print(f"  Total: {len(entries)} entries\n")

    rows = [r for e in entries if (r := entry_to_row(e)) is not None]
    print(f"  Valid rows: {len(rows)}")

    # ── Deduplicate: keep best gap per (molecule, mapping, ansatz, orbital_opt) ─
    # Protects against duplicate JSON files in db/ (e.g., two runs of same config).
    seen: dict[tuple, dict] = {}
    for r in rows:
        key = (r["molecule"], r["mapping"], r["ansatz"], r["orbital_opt"])
        if key not in seen or r["gap"] < seen[key]["gap"]:
            seen[key] = r
    deduped = list(seen.values())
    if len(deduped) < len(rows):
        print(f"  [WARN] Deduplicated {len(rows) - len(deduped)} duplicate row(s) — kept best gap.")
    rows = deduped

    # ── 2. Partition ──────────────────────────────────────────────────────────
    certified = [r for r in rows if r["trust"] == "certified"]
    validated = [r for r in rows if r["trust"] != "certified"]
    print(f"  Certified: {len(certified)}  |  Validated (research): {len(validated)}\n")

    # ── 3. Accuracy leaderboard ───────────────────────────────────────────────
    acc_rows = _rank_rows(certified, key_fn=lambda r: r["gap"], ascending=True)
    acc_csv  = [
        {
            "rank":               r["rank"],
            "entry_id":           r["entry_id"],
            "molecule":           r["molecule"],
            "basis":              r["basis"],
            "orbital_opt":        r["orbital_opt"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "t_gate_estimate":    r["t_gate_estimate"],
            "non_clifford_gates": r["non_clifford_gates"],
            "vqe_energy":         r["vqe_energy"],
            "casci_energy":       r["casci_energy"],
            "hf_energy":          r["hf_energy"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
            "optimizer":          r["optimizer"],
            "optimiser_family":   r["optimiser_family"],
            "amplifies":          r["amplifies"],
            "margin":             r["margin"],
            "chem_accurate":      r["chem_accurate"],
            "robustness":         r["robustness"],
            "at_risk":            r["at_risk"],
        }
        for r in acc_rows
    ]

    # ── 4. Hardware cost leaderboard ──────────────────────────────────────────
    cost_eligible = [r for r in certified if r["twoq"] is not None and r["depth"] is not None]
    cost_rows = _rank_rows(
        cost_eligible,
        key_fn=lambda r: (r["twoq"], r["depth"]),
        ascending=True,
    )
    cost_csv = [
        {
            "rank":               r["rank"],
            "entry_id":           r["entry_id"],
            "molecule":           r["molecule"],
            "basis":              r["basis"],
            "orbital_opt":        r["orbital_opt"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "depth":              r["depth"],
            "2q_gates":           r["twoq"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "t_gate_estimate":    r["t_gate_estimate"],
            "non_clifford_gates": r["non_clifford_gates"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
            "optimizer":          r["optimizer"],
            "optimiser_family":   r["optimiser_family"],
            "amplifies":          r["amplifies"],
            "margin":             r["margin"],
            "chem_accurate":      r["chem_accurate"],
            "robustness":         r["robustness"],
            "at_risk":            r["at_risk"],
        }
        for r in cost_rows
    ]

    # ── 5. Balanced leaderboard ───────────────────────────────────────────────
    balanced_eligible = cost_eligible
    N = len(balanced_eligible)

    if N > 1:
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
            "entry_id":           r["entry_id"],
            "molecule":           r["molecule"],
            "basis":              r["basis"],
            "orbital_opt":        r["orbital_opt"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "depth":              r["depth"],
            "2q_gates":           r["twoq"],
            "balanced_score":     r["balanced_score"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "t_gate_estimate":    r["t_gate_estimate"],
            "non_clifford_gates": r["non_clifford_gates"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
            "optimizer":          r["optimizer"],
            "optimiser_family":   r["optimiser_family"],
            "amplifies":          r["amplifies"],
            "margin":             r["margin"],
            "chem_accurate":      r["chem_accurate"],
            "robustness":         r["robustness"],
            "at_risk":            r["at_risk"],
        }
        for r in balanced_rows
    ]

    # ── 6. Research leaderboard ───────────────────────────────────────────────
    res_rows = _rank_rows(validated, key_fn=lambda r: r["gap"], ascending=True)
    research_csv = [
        {
            "rank":               r["rank"],
            "entry_id":           r["entry_id"],
            "molecule":           r["molecule"],
            "basis":              r["basis"],
            "orbital_opt":        r["orbital_opt"],
            "mapping":            r["mapping"],
            "ansatz":             r["ansatz"],
            "gap":                r["gap"],
            "ccsd_t_correlation": r["ccsd_t_correlation"],
            "t_gate_estimate":    r["t_gate_estimate"],
            "non_clifford_gates": r["non_clifford_gates"],
            "vqe_energy":         r["vqe_energy"],
            "casci_energy":       r["casci_energy"],
            "hf_energy":          r["hf_energy"],
            "baseline":           r["baseline"],
            "beats_classical":    r["beats_classical"],
            "optimizer":          r["optimizer"],
            "optimiser_family":   r["optimiser_family"],
            "amplifies":          r["amplifies"],
            "margin":             r["margin"],
            "chem_accurate":      r["chem_accurate"],
            "robustness":         r["robustness"],
            "at_risk":            r["at_risk"],
        }
        for r in res_rows
    ]

    # ── 7. Metadata ───────────────────────────────────────────────────────────
    beats_count = sum(1 for r in certified if r["beats_classical"] is True)
    metadata = {
        "suite_version":         suite_version,
        "leaderboard_rules":     LEADERBOARD_RULES,
        "generation_date":       datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "entries_included":      len(certified),
        "trust_filter":          "certified_only",
        "beats_classical_count": beats_count,
        "validated_count":       len(validated),
        "default_basis":         "cc-pvdz",
    }

    # ── 8. Summary ────────────────────────────────────────────────────────────
    print(f"  Accuracy:  {len(acc_csv):3} entries")
    print(f"  Cost:      {len(cost_csv):3} entries")
    print(f"  Balanced:  {len(balanced_csv):3} entries")
    print(f"  Research:  {len(research_csv):3} entries")
    print(f"  Beats Classical: {beats_count}/{len(certified)} certified")
    chem  = sum(1 for r in certified if r["chem_accurate"])
    thin  = sum(1 for r in certified if r["margin"] is not None
                and r["margin"] < GAP_THRESHOLD * _cm.THIN_MARGIN_FRACTION)
    risk  = sum(1 for r in certified if r["at_risk"])
    meas  = sum(1 for r in rows if r["robustness"])
    print(f"  Chemical accuracy (<{CHEM_ACCURACY*1e3:.1f} mHa): {chem}/{len(certified)} certified")
    print(f"  Thin margin: {thin}   at-risk (thin + amplifying, unmeasured): {risk}   "
          f"measured across environments: {meas}\n")

    print("  Top 5 Balanced:")
    for r in balanced_csv[:5]:
        print(f"    #{r['rank']}  {r['molecule']:4} {r['basis']}  {r['mapping'][:3].upper()} "
              f"{r['ansatz'][:3].upper()}  gap={r['gap']:.2e}  2q={r['2q_gates']}  "
              f"score={r['balanced_score']:.4f}  beats_classical={r['beats_classical']}")
    print()

    # ── 9. Write files ────────────────────────────────────────────────────────
    MARGIN_FIELDS   = ["optimizer","optimiser_family","amplifies","margin","chem_accurate","robustness","at_risk"]
    ACC_FIELDS      = ["rank","entry_id","molecule","basis","orbital_opt","mapping","ansatz","gap","ccsd_t_correlation","vqe_energy","casci_energy","hf_energy","t_gate_estimate","non_clifford_gates","baseline","beats_classical"] + MARGIN_FIELDS
    COST_FIELDS     = ["rank","entry_id","molecule","basis","orbital_opt","mapping","ansatz","gap","depth","2q_gates","ccsd_t_correlation","t_gate_estimate","non_clifford_gates","baseline","beats_classical"] + MARGIN_FIELDS
    BALANCED_FIELDS = ["rank","entry_id","molecule","basis","orbital_opt","mapping","ansatz","gap","depth","2q_gates","balanced_score","ccsd_t_correlation","t_gate_estimate","non_clifford_gates","baseline","beats_classical"] + MARGIN_FIELDS
    RESEARCH_FIELDS = ACC_FIELDS

    _write_csv(OUTPUT_DIR / "leaderboard_accuracy.csv",      ACC_FIELDS,      acc_csv,      args.dry_run)
    _write_csv(OUTPUT_DIR / "leaderboard_hardware_cost.csv", COST_FIELDS,     cost_csv,     args.dry_run)
    _write_csv(OUTPUT_DIR / "leaderboard_balanced.csv",      BALANCED_FIELDS, balanced_csv, args.dry_run)
    _write_csv(OUTPUT_DIR / "leaderboard_research.csv",      RESEARCH_FIELDS, research_csv, args.dry_run)

    if not args.dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        meta_path = OUTPUT_DIR / "leaderboard_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        print(f"  [OK] leaderboard_metadata.json")
    else:
        print(f"  [DRY-RUN] Would write leaderboard_metadata.json: {metadata}")

    print(f"\n{'='*65}")
    print(f"  DONE — leaderboard exported to {OUTPUT_DIR}")
    print(f"{'='*65}\n")


if __name__ == "__main__":
    main()
