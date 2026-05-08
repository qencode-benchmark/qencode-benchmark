#!/usr/bin/env python3
"""
Rebuild all leaderboard CSVs directly from certified db run files.

For every (molecule, mapping, ansatz) combination, picks the BEST
(lowest gap) certified run. Handles both v1 and v2 file schemas.
Writes:
  website/public/data/leaderboard_accuracy.csv
  website/public/data/leaderboard_hardware_cost.csv
  website/public/data/leaderboard_balanced.csv
  website/public/data/leaderboard_research.csv
  website/public/data/leaderboard_metadata.json
"""

import json, csv, os, glob, re
from pathlib import Path
from datetime import date

REPO    = Path(__file__).resolve().parent.parent
DB_DIR  = REPO / "releases" / "v2" / "db"
OUT_DIR = REPO / "website" / "public" / "data"

RESEARCH_MOLECULES  = {"N2"}
CERTIFIED_THRESHOLD = 0.01   # 10 mHa


def ansatz_from_filename(fname):
    """Fallback: extract ansatz from filename like BeH2_sto3g_JW_uccsd_v1__sha256_xxx"""
    fname = os.path.basename(fname).lower()
    if "hardware_efficient" in fname or "_hweff_" in fname:
        return "hardware_efficient"
    if "uccsd" in fname:
        return "uccsd"
    return None


def load_entry(path):
    with open(path) as f:
        d = json.load(f)

    results = d.get("results", {})
    qual    = results.get("quality", {})
    vqe     = results.get("vqe", {})

    # ── Trust level: v2 uses top-level trust{}, v1 uses results.quality.trusted ──
    trust_obj = d.get("trust", {})
    trust = trust_obj.get("level", "")
    if not trust:
        # v1 schema: results.quality.trusted == True means certified
        if qual.get("trusted") is True:
            trust = "certified"
        elif qual.get("trusted") is False:
            trust = "validated"

    if trust not in ("certified", "validated"):
        return None

    # ── Core fields ──────────────────────────────────────────────────────────
    problem  = d.get("problem", {})
    encoding = d.get("encoding", {})
    circ     = d.get("circuit_stats", {})

    mol     = problem.get("name")
    mapping = encoding.get("mapping")
    ansatz  = encoding.get("ansatz_type") or ansatz_from_filename(path)
    gap     = qual.get("abs_vqe_exact_gap")

    if not all([mol, mapping, ansatz, gap is not None]):
        return None

    # ── Circuit metrics ───────────────────────────────────────────────────────
    # Priority: results.vqe.circuit_metrics (transpiled from actual run)
    #   then: circuit_stats.*_transpiled
    #   then: circuit_stats.*  (raw, non-transpiled)
    # If depth ≤ 1 for UCCSD it is a symbolic placeholder — set to None
    vqe_metrics = vqe.get("circuit_metrics", {})

    depth = (vqe_metrics.get("ansatz_depth")
             or circ.get("ansatz_depth_transpiled")
             or circ.get("ansatz_depth"))
    two_q = (vqe_metrics.get("ansatz_num_2q_gates")
             or circ.get("ansatz_num_2q_gates_transpiled")
             or circ.get("ansatz_num_2q_gates"))

    if depth is not None:
        depth = int(depth)
    if two_q is not None:
        two_q = int(two_q)

    # Treat depth=1 / 2Q=1 for UCCSD as symbolic (not transpiled)
    if ansatz == "uccsd" and (depth or 0) <= 1:
        depth = None
        two_q = None

    return {
        "molecule": mol,
        "mapping":  mapping,
        "ansatz":   ansatz,
        "gap":      gap,
        "depth":    depth,
        "two_q":    two_q,
        "trust":    trust,
        "date":     d.get("created_utc", "")[:10],
        "file":     os.path.basename(path),
    }


def best_per_combo(entries):
    """Keep the single lowest-gap run per (mol, mapping, ansatz)."""
    bests = {}
    for e in entries:
        key = (e["molecule"], e["mapping"], e["ansatz"])
        if key not in bests or e["gap"] < bests[key]["gap"]:
            bests[key] = e
    return list(bests.values())


def write_csv(path, headers, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        for r in rows:
            w.writerow(r)
    print(f"  wrote {path.name}  ({len(rows)} rows)")


def main():
    print(f"Reading db files from: {DB_DIR}\n")
    files = glob.glob(str(DB_DIR / "*.json"))
    files = [f for f in files if not any(
        x in os.path.basename(f) for x in ("index", "manifest", "benchmarks")
    )]
    print(f"  {len(files)} JSON files found")

    entries, skipped = [], 0
    for path in sorted(files):
        e = load_entry(path)
        if e:
            entries.append(e)
        else:
            skipped += 1
    print(f"  {len(entries)} valid entries loaded, {skipped} skipped\n")

    certified_entries = [e for e in entries
                         if e["molecule"] not in RESEARCH_MOLECULES
                         and e["trust"] == "certified"
                         and e["gap"] < CERTIFIED_THRESHOLD]
    research_entries  = [e for e in entries
                         if e["molecule"] in RESEARCH_MOLECULES]

    best_cert     = best_per_combo(certified_entries)
    best_research = best_per_combo(research_entries)

    molecules = sorted(set(e["molecule"] for e in best_cert))
    print(f"Certified molecules : {molecules}")
    print(f"Research molecules  : {sorted(set(e['molecule'] for e in best_research))}\n")

    print(f"  {'Mol':<6} {'Mapping':<20} {'Ansatz':<22} {'Gap':>12}  {'Depth':>6}  {'2Q':>6}  Trust       Date")
    print("  " + "-"*95)
    for e in sorted(best_cert, key=lambda x: (x["molecule"], x["mapping"], x["ansatz"])):
        d_s = str(e["depth"]) if e["depth"] else "N/A"
        q_s = str(e["two_q"]) if e["two_q"] else "N/A"
        print(f"  {e['molecule']:<6} {e['mapping']:<20} {e['ansatz']:<22}"
              f" {e['gap']:>12.4e}  {d_s:>6}  {q_s:>6}  {e['trust']:<11} {e['date']}")

    # ── Accuracy: rank by lowest gap per molecule ─────────────────────────────
    acc_rows = []
    for mol in molecules:
        mol_e = sorted([e for e in best_cert if e["molecule"] == mol],
                       key=lambda x: (x["gap"], x["depth"] or 99999))
        for rank, e in enumerate(mol_e, 1):
            acc_rows.append([rank, e["molecule"], e["mapping"], e["ansatz"],
                             e["gap"], e["depth"], e["two_q"], False])

    # ── Hardware cost: rank by fewest 2Q then depth (skip null metrics) ───────
    cost_rows = []
    for mol in molecules:
        mol_e = sorted([e for e in best_cert
                        if e["molecule"] == mol and e["two_q"] and e["depth"]],
                       key=lambda x: (x["two_q"], x["depth"]))
        for rank, e in enumerate(mol_e, 1):
            cost_rows.append([rank, e["molecule"], e["mapping"], e["ansatz"],
                              e["gap"], e["depth"], e["two_q"], False])

    # ── Balanced: gap × depth (skip entries with null depth) ─────────────────
    bal_rows = []
    for mol in molecules:
        mol_e = sorted([e for e in best_cert
                        if e["molecule"] == mol and e["depth"]],
                       key=lambda x: x["gap"] * x["depth"])
        for rank, e in enumerate(mol_e, 1):
            score = e["gap"] * e["depth"]
            bal_rows.append([rank, e["molecule"], e["mapping"], e["ansatz"],
                             e["gap"], e["depth"], e["two_q"], score, False])

    # ── Research ──────────────────────────────────────────────────────────────
    res_rows = []
    for mol in sorted(set(e["molecule"] for e in best_research)):
        mol_e = sorted([e for e in best_research if e["molecule"] == mol],
                       key=lambda x: x["gap"])
        for rank, e in enumerate(mol_e, 1):
            res_rows.append([rank, e["molecule"], e["mapping"], e["ansatz"],
                             e["gap"], e["depth"], e["two_q"], False])

    print()
    write_csv(OUT_DIR / "leaderboard_accuracy.csv",
              ["rank","molecule","mapping","ansatz","gap","depth","2q_gates","baseline"],
              acc_rows)
    write_csv(OUT_DIR / "leaderboard_hardware_cost.csv",
              ["rank","molecule","mapping","ansatz","gap","depth","2q_gates","baseline"],
              cost_rows)
    write_csv(OUT_DIR / "leaderboard_balanced.csv",
              ["rank","molecule","mapping","ansatz","gap","depth","2q_gates","balanced_score","baseline"],
              bal_rows)
    write_csv(OUT_DIR / "leaderboard_research.csv",
              ["rank","molecule","mapping","ansatz","gap","depth","2q_gates","baseline"],
              res_rows)

    meta = {
        "suite_version":             "v2",
        "leaderboard_rules":         "v1",
        "generation_date":           str(date.today()),
        "entries_included":          len(acc_rows),
        "research_entries_included": len(res_rows),
        "trust_filter":              "certified_only",
        "min_trust_level":           "certified",
    }
    with open(OUT_DIR / "leaderboard_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  wrote leaderboard_metadata.json")

    print(f"\nDone. {len(acc_rows)} certified entries across {len(molecules)} molecules.")
    print(f"      {len(res_rows)} research entries.")


if __name__ == "__main__":
    main()
