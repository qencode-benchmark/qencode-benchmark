#!/usr/bin/env python3
"""
One-time rehash script for Suite v3 / v3.1 entries.

The original entries were hashed with git_commit included in provenance.
After fixing generate_entry_v3.py to exclude git_commit from the hash
(so hashes are stable across commits), this script recomputes entry_hash_sha256
for all stored entries in-place.

entry_id and filenames are NOT changed — only entry_hash_sha256 is updated.

Usage:
  python scripts/rehash_entries_v3.py                       # dry run
  python scripts/rehash_entries_v3.py --write               # write changes
  python scripts/rehash_entries_v3.py --db-dir releases/v3.1/db --write
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def stable_hash(d: dict) -> str:
    """SHA-256 of canonical JSON (sorted keys, compact separators)."""
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def rehash_entry(entry: dict) -> tuple[str, str]:
    """
    Recompute the entry hash excluding git_commit from provenance.
    Returns (old_hash, new_hash).
    """
    old_hash = entry.get("provenance", {}).get("entry_hash_sha256", "")

    # Work on a copy of provenance without git_commit
    import copy
    work = copy.deepcopy(entry)
    work["provenance"].pop("git_commit", None)
    # Also clear the hash and entry_id fields (as the generator does before hashing)
    work["provenance"]["entry_hash_sha256"] = ""
    work["entry_id"] = None
    if "trust" in work:
        work["trust"]["signature_b64"] = None
        work["trust"]["signing_key_id"] = None

    new_hash = stable_hash(work)
    return old_hash, new_hash


def main():
    ap = argparse.ArgumentParser(description="Rehash v3 entries to exclude git_commit.")
    ap.add_argument("--db-dir", default=None,
                    help="Path to db directory (default: both v3 and v3.1)")
    ap.add_argument("--write", action="store_true",
                    help="Write updated hashes to disk (default: dry run)")
    args = ap.parse_args()

    if args.db_dir:
        db_dirs = [Path(args.db_dir)]
    else:
        db_dirs = [
            REPO / "releases" / "v3" / "db",
            REPO / "releases" / "v3.1" / "db",
        ]

    total = changed = 0

    for db_dir in db_dirs:
        if not db_dir.exists():
            continue
        files = sorted(db_dir.glob("*.json"))
        # Skip non-entry files
        files = [f for f in files if "sha256" in f.name]
        print(f"\n{db_dir} — {len(files)} entries")

        for fpath in files:
            entry = json.loads(fpath.read_text())
            old_hash, new_hash = rehash_entry(entry)
            total += 1

            if old_hash == new_hash:
                print(f"  OK  {fpath.name[:60]}")
                continue

            changed += 1
            print(f"  UPD {fpath.name[:60]}")
            print(f"       old: {old_hash[:16]}…")
            print(f"       new: {new_hash[:16]}…")

            if args.write:
                entry["provenance"]["entry_hash_sha256"] = new_hash
                fpath.write_text(json.dumps(entry, indent=2, ensure_ascii=True))

    print(f"\n{'Wrote' if args.write else 'Would update'} {changed}/{total} entries.")
    if not args.write and changed > 0:
        print("Run with --write to apply changes.")


if __name__ == "__main__":
    main()
