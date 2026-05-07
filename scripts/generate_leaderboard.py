#!/usr/bin/env python3
"""
Phase 18: Leaderboard dataset generator.

Converts certified benchmark results into leaderboard CSV tables:
- leaderboard_accuracy.csv
- leaderboard_hardware_cost.csv
- leaderboard_balanced.csv
- leaderboard_research.csv   ← validated (not certified) entries, e.g. N2 [6,6]

Defaults:
- trust_level: certified (main leaderboard)
- gap metric: gap_ideal (v1)
- balanced score: gap * depth  (v1)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pandas as pd

from qencode.comparison_engine import full_comparison, list_molecules, sync_from_dir
from qencode.leaderboard.model import compute_balanced_score, create_leaderboard_entry


GAP_TIE_DECIMALS = 12


def _rank_within_molecule(df: pd.DataFrame, sort_cols: List[str]) -> pd.DataFrame:
    out = df.sort_values(sort_cols, ascending=True, na_position="last").copy()
    out["rank"] = out.groupby("molecule").cumcount() + 1
    return out


def _load_baseline_set(path: Path) -> set[tuple[str, str, str]]:
    """
    Return a set of baseline keys (molecule, mapping, ansatz).

    Baselines are defined in YAML under benchmarks/baselines/baseline_v1.yaml.
    We intentionally keep matching lightweight so leaderboards can mark baseline rows
    without requiring basis/active_space columns in the CSVs.
    """
    try:
        import yaml
    except Exception:
        # Baseline marking is optional; if yaml isn't available, just skip.
        return set()

    if not path.exists():
        return set()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = raw.get("baselines") or []
    keys: set[tuple[str, str, str]] = set()
    for b in items:
        mol = str(b.get("molecule") or "").strip()
        mapping = str(b.get("mapping") or "").strip()
        ansatz = str(b.get("ansatz") or "").strip()
        if mol and mapping and ansatz:
            keys.add((mol, mapping, ansatz))
    return keys


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate leaderboard CSVs from certified benchmark results")
    ap.add_argument("--db-dir", default="releases/v2/db", help="v2 DB directory (source for sync)")
    ap.add_argument("--sqlite", default=None, help="SQLite path (default: <db-dir>/benchmarks.db)")
    ap.add_argument("--out-dir", default="datasets/leaderboard", help="Output directory for leaderboard CSVs")
    ap.add_argument("--variant", default="default")
    ap.add_argument("--basis", default="sto3g")
    ap.add_argument("--gap-key", default="gap_ideal", choices=("gap_ideal", "gap_noisy"), help="Which gap metric to use for leaderboard (v1 default: gap_ideal)")
    ap.add_argument("--baseline-file", default="benchmarks/baselines/baseline_v1.yaml", help="Baseline YAML file to mark baseline entries")
    ap.add_argument("--require-official-receipts", action="store_true", help="Only include certified entries with valid signed receipts (option B)")
    args = ap.parse_args()

    repo = _REPO
    db_dir = Path(args.db_dir)
    if not db_dir.is_absolute():
        db_dir = (repo / db_dir).resolve()
    if not db_dir.is_dir():
        sys.exit(f"db-dir not found: {db_dir}")

    sqlite_path = Path(args.sqlite) if args.sqlite else (db_dir / "benchmarks.db")
    if not sqlite_path.is_absolute():
        sqlite_path = (repo / sqlite_path).resolve()

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (repo / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.require_official_receipts:
        os.environ["QENCODE_REQUIRE_OFFICIAL_RECEIPTS"] = "1"

    baseline_file = Path(args.baseline_file)
    if not baseline_file.is_absolute():
        baseline_file = (repo / baseline_file).resolve()
    baseline_keys = _load_baseline_set(baseline_file)

    # Always sync so trust_level updates are reflected in SQLite
    n = sync_from_dir(db_dir, sqlite_path)

    molecules = list_molecules(sqlite_path)
    if not molecules:
        sys.exit("No molecules found in SQLite. Run benchmarks first.")

    rows: List[Dict[str, Any]] = []
    for mol in molecules:
        r = full_comparison(
            sqlite_path,
            mol,
            variant=args.variant,
            basis=args.basis,
            trust_level="certified",
        )
        rows.extend(r.get("rows") or [])

    if not rows:
        sys.exit("No certified rows found. Run assign_trust_levels.py then re-sync.")

    entries = [
        create_leaderboard_entry(row, gap_key=args.gap_key, backend=("noisy" if args.gap_key == "gap_noisy" else "ideal"))
        for row in rows
    ]
    df = pd.DataFrame(entries)

    # Keep only rankable rows
    df = df[df["molecule"].notna()].copy()
    if baseline_keys:
        df["baseline"] = df.apply(
            lambda r: (str(r.get("molecule")), str(r.get("mapping")), str(r.get("ansatz"))) in baseline_keys,
            axis=1,
        )
    else:
        df["baseline"] = False

    # --- Best Accuracy ---
    # Use tie-tolerant gap sorting so near-equal floating values fall back to
    # deterministic tie-breakers (depth first, then 2q gates).
    df_acc = df[df["gap"].notna()].copy()
    df_acc["gap_sort"] = df_acc["gap"].round(GAP_TIE_DECIMALS)
    df_acc = _rank_within_molecule(df_acc, ["molecule", "gap_sort", "depth", "two_qubit_gates"])
    df_acc_out = df_acc[["rank", "molecule", "mapping", "ansatz", "gap", "depth", "two_qubit_gates", "baseline"]].rename(
        columns={"two_qubit_gates": "2q_gates"}
    )
    acc_path = out_dir / "leaderboard_accuracy.csv"
    df_acc_out.to_csv(acc_path, index=False)

    # --- Lowest Hardware Cost ---
    df_cost = df[df["two_qubit_gates"].notna()].copy()
    df_cost = _rank_within_molecule(df_cost, ["molecule", "two_qubit_gates", "gap", "depth"])
    df_cost_out = df_cost[["rank", "molecule", "mapping", "ansatz", "gap", "depth", "two_qubit_gates", "baseline"]].rename(
        columns={"two_qubit_gates": "2q_gates"}
    )
    cost_path = out_dir / "leaderboard_hardware_cost.csv"
    df_cost_out.to_csv(cost_path, index=False)

    # --- Best Balanced ---
    df_bal = df.copy()
    df_bal["balanced_score"] = df_bal.apply(lambda r: compute_balanced_score(r.to_dict()), axis=1)
    df_bal = df_bal[df_bal["balanced_score"].notna()].copy()
    df_bal = _rank_within_molecule(df_bal, ["molecule", "balanced_score", "gap", "two_qubit_gates"])
    df_bal_out = df_bal[
        ["rank", "molecule", "mapping", "ansatz", "gap", "depth", "two_qubit_gates", "balanced_score", "baseline"]
    ].rename(columns={"two_qubit_gates": "2q_gates"})
    bal_path = out_dir / "leaderboard_balanced.csv"
    df_bal_out.to_csv(bal_path, index=False)

    # --- Research tier (validated, not certified) ---
    # Only includes molecules that have ZERO certified entries (e.g. N2 [6,6] whose
    # gap exceeds the 0.01 Ha certification threshold due to strong electron
    # correlation). Molecules that are partially certified (e.g. H2O with some
    # unconverged HEA variants) are excluded — those non-certified variants are just
    # convergence failures, not scientifically interesting research entries.
    certified_molecules = {e["molecule"] for e in entries}
    certified_keys = {(e["molecule"], e["mapping"], e["ansatz"]) for e in entries}

    research_rows: List[Dict[str, Any]] = []
    for mol in molecules:
        # Skip molecules that already have at least one certified entry
        if mol in certified_molecules:
            continue
        r = full_comparison(
            sqlite_path,
            mol,
            variant=args.variant,
            basis=args.basis,
            trust_level="validated",
        )
        mol_rows = r.get("rows") or []
        for row in mol_rows:
            key = (row.get("molecule"), row.get("mapping"), row.get("ansatz_type"))
            if key not in certified_keys:
                research_rows.append(row)

    if research_rows:
        research_entries = [
            create_leaderboard_entry(row, gap_key=args.gap_key, backend="ideal")
            for row in research_rows
        ]
        df_res = pd.DataFrame(research_entries)
        df_res = df_res[df_res["molecule"].notna()].copy()
        df_res["gap_sort"] = df_res["gap"].round(GAP_TIE_DECIMALS)
        df_res = _rank_within_molecule(df_res, ["molecule", "gap_sort", "depth", "two_qubit_gates"])
        df_res["baseline"] = False
        df_res_out = df_res[["rank", "molecule", "mapping", "ansatz", "gap", "depth", "two_qubit_gates", "baseline"]].rename(
            columns={"two_qubit_gates": "2q_gates"}
        )
        res_path = out_dir / "leaderboard_research.csv"
        df_res_out.to_csv(res_path, index=False)
        print(f"Wrote: {res_path}  ({len(df_res_out)} research-tier entries)")
    else:
        res_path = out_dir / "leaderboard_research.csv"
        pd.DataFrame(columns=["rank","molecule","mapping","ansatz","gap","depth","2q_gates","baseline"]).to_csv(res_path, index=False)
        print(f"Wrote: {res_path}  (0 research-tier entries)")

    print(f"Synced {n} rows to SQLite: {sqlite_path}")
    print(f"Wrote: {acc_path}")
    print(f"Wrote: {cost_path}")
    print(f"Wrote: {bal_path}")


if __name__ == "__main__":
    main()

