#!/usr/bin/env python3
"""
publish_leaderboard_live.py
===========================
Reads the generated leaderboard CSVs and metadata, then POSTs them to the
live website's admin endpoint so the leaderboard updates without a redeploy.

Usage (from Ubuntu):
    cd ~/work/qencode-db
    conda activate qencode
    python scripts/publish_leaderboard_live.py

Or after generating a fresh leaderboard:
    python scripts/generate_leaderboard.py && python scripts/publish_leaderboard_live.py

Environment:
    LEADERBOARD_PUBLISH_SECRET  — must match the value set in Vercel env vars
                                   Set it in ~/.bashrc or export before running:
                                   export LEADERBOARD_PUBLISH_SECRET=your_secret_here

    QENCODE_API_URL             — override if testing against a preview URL
                                   defaults to https://www.qencode-benchmark.org
"""

import csv
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("requests is not installed. Run: pip install requests")

# ── Config ────────────────────────────────────────────────────────────────────

REPO_ROOT   = Path(__file__).parent.parent
DATASET_DIR = REPO_ROOT / "datasets" / "leaderboard"
METADATA_FILE = REPO_ROOT / "website" / "public" / "data" / "leaderboard_metadata.json"

API_URL = os.environ.get(
    "QENCODE_API_URL",
    "https://www.qencode-benchmark.org"
).rstrip("/")

ENDPOINT = f"{API_URL}/api/admin/publish-leaderboard"

SECRET = os.environ.get("LEADERBOARD_PUBLISH_SECRET", "").strip().lstrip("﻿")

CHAIN_FILE = REPO_ROOT / "LEADERBOARD_CHAIN.jsonl"

# ── Helpers ───────────────────────────────────────────────────────────────────

def read_csv(filepath: Path) -> list[dict]:
    """Parse a leaderboard CSV into a list of dicts."""
    if not filepath.exists():
        sys.exit(f"ERROR: CSV not found: {filepath}\nRun generate_leaderboard.py first.")
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def to_num(value, cast=float):
    """Convert CSV string to number, returning None for empty/missing."""
    if value is None or str(value).strip() == "":
        return None
    try:
        return cast(value)
    except (ValueError, TypeError):
        return None


def normalize_entry(row: dict, category: str) -> dict:
    """Convert a raw CSV row to the JSON shape expected by the API."""
    return {
        "rank":          to_num(row.get("rank"), int),
        "molecule":      row.get("molecule", "").strip(),
        "mapping":       row.get("mapping",  "").strip(),
        "ansatz":        row.get("ansatz",   "").strip(),
        "gap":           to_num(row.get("gap")),
        "depth":         to_num(row.get("depth"),       int),
        "two_q_gates":   to_num(row.get("2q_gates"),    int),
        "balanced_score": to_num(row.get("balanced_score")) if category == "balanced" else None,
        "baseline":      str(row.get("baseline", "false")).strip().lower() == "true",
    }


def compute_payload_hash(payload: dict) -> str:
    """SHA-256 hash of the canonical JSON representation of the payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_chain_block(payload: dict, entries_count: dict) -> str:
    """
    Append a new block to the Merkle-style audit chain.
    Each block contains:
      - block: sequential block number
      - timestamp: ISO 8601 UTC
      - prev_hash: hash of the previous block (or "genesis" for block 0)
      - hash: SHA-256 of (prev_hash + canonical payload JSON)
      - entries: count per category
    Returns the hash of the new block.
    """
    # Read previous block
    prev_hash = "genesis"
    block_num = 0
    if CHAIN_FILE.exists():
        lines = CHAIN_FILE.read_text(encoding="utf-8").strip().splitlines()
        if lines:
            last = json.loads(lines[-1])
            prev_hash = last["hash"]
            block_num = last["block"] + 1

    # Compute hash: SHA-256(prev_hash + canonical payload)
    combined = prev_hash + json.dumps(payload, sort_keys=True, ensure_ascii=False)
    block_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    block = {
        "block":     block_num,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "prev_hash": prev_hash,
        "hash":      block_hash,
        "entries":   entries_count,
    }

    with open(CHAIN_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(block) + "\n")

    return block_hash


def load_metadata() -> dict:
    """Load leaderboard metadata from the JSON file."""
    if not METADATA_FILE.exists():
        print(f"WARNING: metadata file not found at {METADATA_FILE}, using defaults")
        return {
            "suite_version":    "v2",
            "leaderboard_rules": "v1",
            "generation_date":  str(date.today()),
            "trust_filter":     "certified_only",
        }
    with open(METADATA_FILE, encoding="utf-8") as f:
        return json.load(f)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not SECRET:
        sys.exit(
            "ERROR: LEADERBOARD_PUBLISH_SECRET is not set.\n"
            "Export it before running:\n"
            "  export LEADERBOARD_PUBLISH_SECRET=your_secret_here\n"
            "The value must match what is set in Vercel → Environment Variables."
        )

    print(f"Reading leaderboard data from {DATASET_DIR}")

    accuracy = [normalize_entry(r, "accuracy") for r in read_csv(DATASET_DIR / "leaderboard_accuracy.csv")]
    cost     = [normalize_entry(r, "cost")     for r in read_csv(DATASET_DIR / "leaderboard_hardware_cost.csv")]
    balanced = [normalize_entry(r, "balanced") for r in read_csv(DATASET_DIR / "leaderboard_balanced.csv")]
    metadata = load_metadata()

    # Strip internal absolute paths from metadata before publishing
    metadata.pop("source_datasets",      None)
    metadata.pop("audit_report",         None)
    metadata.pop("generation_command",   None)
    metadata.pop("certified_receipts_file", None)

    # Research tier: validated entries not in the certified leaderboard (e.g. N2 [6,6]).
    research_csv = DATASET_DIR / "leaderboard_research.csv"
    research = [normalize_entry(r, "research") for r in read_csv(research_csv)] if research_csv.exists() else []

    # Derive entry count from the accuracy table (most complete)
    metadata["entries_included"] = str(len(accuracy))
    metadata["research_entries_included"] = str(len(research))

    payload = {
        "accuracy": accuracy,
        "cost":     cost,
        "balanced": balanced,
        "research": research,
        "metadata": metadata,
    }

    print(f"Entries — accuracy: {len(accuracy)}, cost: {len(cost)}, balanced: {len(balanced)}")
    print(f"Posting to {ENDPOINT} ...")

    try:
        resp = requests.post(
            ENDPOINT,
            json=payload,
            headers={
                "Authorization": f"Bearer {SECRET}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
    except requests.exceptions.RequestException as e:
        sys.exit(f"ERROR: Request failed: {e}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"\n✓ Leaderboard published successfully!")
        print(f"  accuracy: {data['published']['accuracy']} entries")
        print(f"  cost:     {data['published']['cost']} entries")
        print(f"  balanced: {data['published']['balanced']} entries")
        print(f"  research: {data['published'].get('research', 0)} entries")

        # Append audit chain block
        block_hash = append_chain_block(
            payload,
            entries_count={
                "accuracy": data["published"]["accuracy"],
                "cost":     data["published"]["cost"],
                "balanced": data["published"]["balanced"],
                "research": data["published"].get("research", len(research)),
            }
        )
        print(f"\n🔗 Audit chain updated")
        print(f"  Block hash: {block_hash[:16]}...{block_hash[-8:]}")
        print(f"  Chain file: {CHAIN_FILE}")
        print(f"\n  Commit the chain file to make the audit trail public:")
        print(f"  git add LEADERBOARD_CHAIN.jsonl && git commit -m 'audit: leaderboard block {block_hash[:8]}'")
        print(f"\nThe /leaderboard page will reflect the new data on next visit.")
    else:
        print(f"\n✗ Publish failed (HTTP {resp.status_code})")
        try:
            print(json.dumps(resp.json(), indent=2))
        except Exception:
            print(resp.text)
        sys.exit(1)


if __name__ == "__main__":
    main()
