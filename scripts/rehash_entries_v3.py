#!/usr/bin/env python3
"""
One-time rehash script for Suite v3 / v3.1 entries.

Recomputes entry_hash_sha256 for all stored entries using the same
volatile-field exclusion as the fixed generate_entry_v3.py:
  - timestamps (created_utc, computed_utc, certified_utc)
  - git_commit, entry_id, signature fields

entry_id and filenames are NOT changed — only entry_hash_sha256 is updated.

Usage:
  python scripts/rehash_entries_v3.py                       # dry run
  python scripts/rehash_entries_v3.py --write               # write changes
  python scripts/rehash_entries_v3.py --db-dir releases/v3.1/db --write
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Must match _HASH_EXCLUDE in generate_entry_v3.py exactly
_HASH_EXCLUDE = {
    "created_utc", "entry_id", "entry_hash_sha256",
    "git_commit",
    "computed_utc", "certified_utc",
    "signature_b64", "signing_key_id",
}


def _strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: _strip_volatile(v) for k, v in obj.items() if k not in _HASH_EXCLUDE}
    if isinstance(obj, list):
        return [_strip_volatile(v) for v in obj]
    return copy.deepcopy(obj)


def stable_hash(d: dict) -> str:
    canonical = json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def rehash_entry(entry: dict) -> tuple[str, str]:
    """Returns (old_hash, new_hash)."""
    old_hash = entry.get("provenance", {}).get("entry_hash_sha256", "")
    new_hash = stable_hash(_strip_volatile(entry))
    return old_hash, new_hash


def main():
    ap = argparse.ArgumentParser(description="Rehash v3 entries excluding volatile fields.")
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
        files = sorted(f for f in db_dir.glob("*.json") if "sha256" in f.name)
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
