#!/usr/bin/env python3
"""
QEncode — Publish leaderboard CSVs to production database
==========================================================
Reads the 4 CSV files from website/public/data/ and POSTs them to
the /api/admin/publish-leaderboard endpoint, replacing whatever is
currently in the Neon Postgres database.

Usage:
    python scripts/publish_leaderboard.py \
        --secret YOUR_LEADERBOARD_PUBLISH_SECRET \
        [--url https://qencode-benchmark.org]

Or set env var:
    export LEADERBOARD_PUBLISH_SECRET=your_secret
    python scripts/publish_leaderboard.py
"""

import argparse
import csv
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "website" / "public" / "data"
DEFAULT_URL = "https://qencode-benchmark.org"

# ── CSV parsing ───────────────────────────────────────────────────────────────
def num(v):
    if v in (None, "", "None", "null"): return None
    try:   return float(v)
    except: return None

def bool_val(v):
    return str(v).strip().lower() in ("true", "1", "yes")

def parse_accuracy_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "rank":               int(r["rank"]),
                "molecule":           r["molecule"],
                "mapping":            r["mapping"],
                "ansatz":             r["ansatz"],
                "gap":                num(r["gap"]),
                "depth":              num(r.get("depth")),
                "two_q_gates":        num(r.get("2q_gates")),
                "baseline":           bool_val(r.get("baseline", False)),
                "beats_classical":    bool_val(r.get("beats_classical", False)) if r.get("beats_classical") not in (None, "", "None", "null") else None,
                "ccsd_t_correlation": num(r.get("ccsd_t_correlation")),
                "vqe_energy":         num(r.get("vqe_energy")),
                "casci_energy":       num(r.get("casci_energy")),
                "hf_energy":          num(r.get("hf_energy")),
            })
    return rows

def parse_cost_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "rank":               int(r["rank"]),
                "molecule":           r["molecule"],
                "mapping":            r["mapping"],
                "ansatz":             r["ansatz"],
                "gap":                num(r["gap"]),
                "depth":              num(r.get("depth")),
                "two_q_gates":        num(r.get("2q_gates")),
                "baseline":           bool_val(r.get("baseline", False)),
                "beats_classical":    bool_val(r.get("beats_classical", False)) if r.get("beats_classical") not in (None, "", "None", "null") else None,
                "ccsd_t_correlation": num(r.get("ccsd_t_correlation")),
                "vqe_energy":         num(r.get("vqe_energy")),
                "casci_energy":       num(r.get("casci_energy")),
                "hf_energy":          num(r.get("hf_energy")),
            })
    return rows

def parse_balanced_csv(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "rank":               int(r["rank"]),
                "molecule":           r["molecule"],
                "mapping":            r["mapping"],
                "ansatz":             r["ansatz"],
                "gap":                num(r["gap"]),
                "depth":              num(r.get("depth")),
                "two_q_gates":        num(r.get("2q_gates")),
                "balanced_score":     num(r.get("balanced_score")),
                "baseline":           bool_val(r.get("baseline", False)),
                "beats_classical":    bool_val(r.get("beats_classical", False)) if r.get("beats_classical") not in (None, "", "None", "null") else None,
                "ccsd_t_correlation": num(r.get("ccsd_t_correlation")),
                "vqe_energy":         num(r.get("vqe_energy")),
                "casci_energy":       num(r.get("casci_energy")),
                "hf_energy":          num(r.get("hf_energy")),
            })
    return rows

def parse_research_csv(path):
    return parse_accuracy_csv(path)  # same shape

def parse_metadata(path):
    with open(path) as f:
        return json.load(f)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Publish leaderboard CSVs to production DB")
    parser.add_argument("--secret", default=os.environ.get("LEADERBOARD_PUBLISH_SECRET",""),
                        help="LEADERBOARD_PUBLISH_SECRET value")
    parser.add_argument("--url",    default=DEFAULT_URL,
                        help=f"Base URL (default: {DEFAULT_URL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the payload but don't send it")
    args = parser.parse_args()

    if not args.secret and not args.dry_run:
        print("ERROR: provide --secret or set LEADERBOARD_PUBLISH_SECRET")
        sys.exit(1)

    # ── Load files ─────────────────────────────────────────────────────────────
    acc_path      = DATA_DIR / "leaderboard_accuracy.csv"
    cost_path     = DATA_DIR / "leaderboard_hardware_cost.csv"
    balanced_path = DATA_DIR / "leaderboard_balanced.csv"
    research_path = DATA_DIR / "leaderboard_research.csv"
    meta_path     = DATA_DIR / "leaderboard_metadata.json"

    for p in [acc_path, cost_path, balanced_path, meta_path]:
        if not p.exists():
            print(f"ERROR: file not found: {p}")
            sys.exit(1)

    print("Reading CSV files...")
    accuracy  = parse_accuracy_csv(acc_path)
    cost      = parse_cost_csv(cost_path)
    balanced  = parse_balanced_csv(balanced_path)
    research  = parse_research_csv(research_path) if research_path.exists() else []
    metadata  = parse_metadata(meta_path)

    print(f"  accuracy:  {len(accuracy)} rows")
    print(f"  cost:      {len(cost)} rows")
    print(f"  balanced:  {len(balanced)} rows")
    print(f"  research:  {len(research)} rows")
    print(f"  metadata:  {metadata}")

    # ── Molecule summary ───────────────────────────────────────────────────────
    mols = sorted(set(r["molecule"] for r in accuracy))
    print(f"\nMolecules in accuracy: {mols}")

    payload = {
        "accuracy": accuracy,
        "cost":     cost,
        "balanced": balanced,
        "research": research,
        "metadata": metadata,
    }

    if args.dry_run:
        print("\n-- DRY RUN -- payload (first 2 rows each) --")
        for k in ["accuracy","cost","balanced","research"]:
            print(f"\n  {k}:")
            for row in payload[k][:2]:
                print(f"    {row}")
        print("\nNot sending (--dry-run). Remove flag to publish.")
        return

    # ── POST to API ────────────────────────────────────────────────────────────
    endpoint = args.url.rstrip("/") + "/api/admin/publish-leaderboard"
    body     = json.dumps(payload).encode("utf-8")
    req      = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.secret}",
            # Bypass Cloudflare/Vercel WAF (error 1010) on automated POST requests
            "x-vercel-protection-bypass": "4sSOP9JIfrN0ZfLfkex41oDGOZYfxSgZ",
        },
        method="POST",
    )

    print(f"\nPOSTing to {endpoint} ...")
    # Use an unverified SSL context to work around certificate chain issues on some systems
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
            data = json.loads(resp.read())
            print(f"[OK] Success: {data}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[FAIL] HTTP {e.code}: {body}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Request failed: {e}")
        sys.exit(1)

    print("\nLeaderboard updated. The website will show the new data immediately.")

if __name__ == "__main__":
    main()
