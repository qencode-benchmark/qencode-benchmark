#!/usr/bin/env python3
"""Move regenerated entries into the published database, archiving what they supersede.

    python tools/apply_regenerated.py --dry-run
    python tools/apply_regenerated.py

Superseded entries are moved to releases/v4/db_superseded/ rather than deleted: they were
published, they are cited, and a reader who has one needs to be able to find out what
happened to it. The archive carries a README naming the fault and the replacement.

Written for the 2026-09-07 Z2 sector fix.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "releases" / "v4" / "db"
REGEN = ROOT / "releases" / "v4" / "db_regen"
ARCHIVE = ROOT / "releases" / "v4" / "db_superseded"

README = """# Superseded entries

These entries were published and are now replaced. They are kept, not deleted, because
they were cited and because a reader holding one needs to be able to find out why it
changed. Each is listed below with the entry that replaces it.

## 2026-09-07 — Z2 symmetry sector fix

Every entry here used a fermion-to-qubit mapping other than Jordan-Wigner. The pipeline
derived the Z2 tapering sector with `pennylane.qchem.optimal_sector`, which hard-codes the
Jordan-Wigner Hartree-Fock occupation string and matches generator support against an
unordered set of wires. Both are wrong for parity and Bravyi-Kitaev.

Two consequences, and an entry here has one or both:

* **Wrong sector.** The tapered Hamiltonian was the restriction of H to a symmetry sector
  that does not contain the ground state, with a minimum 0.30 to 0.76 Ha above CASCI. A
  "constant correction" then added that difference back to every energy, which made the
  numbers look right and hid the fault.
* **Wrong Hartree-Fock reference.** `qchem.taper_hf` builds the reference state with the
  Jordan-Wigner transform whatever the mapping, so the circuit did not start from the
  Hartree-Fock determinant. Entries with this fault alone kept a correct Hamiltonian and a
  correct gap; only the starting state was mislabelled.

Full account: `docs/SECTOR_FIX.md`. The fix is commit {commit}.

| superseded entry | replaced by | what was wrong |
|---|---|---|
{table}
"""


def key(e):
    enc = e["encoding"]
    return (e["problem"]["name"], enc["mapping"], enc["ansatz_type"], enc["ansatz_reps"],
            e["problem"]["orbital_optimization"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--commit", default="ab7185b")
    a = ap.parse_args()

    if not REGEN.is_dir():
        raise SystemExit("no regenerated entries at %s" % REGEN)

    old_by_key = {}
    for f in DB.glob("*.json"):
        old_by_key.setdefault(key(json.loads(f.read_text())), []).append(f)

    moves, rows = [], []
    for f in sorted(REGEN.glob("*.json")):
        new = json.loads(f.read_text())
        k = key(new)
        olds = old_by_key.get(k, [])
        if len(olds) != 1:
            raise SystemExit("expected exactly one published entry for %s, found %d" % (k, len(olds)))
        old_file = olds[0]
        old = json.loads(old_file.read_text())
        ot, nt = old["encoding"]["tapering"], new["encoding"]["tapering"]
        sector_changed = list(map(int, ot["sectors"])) != list(map(int, nt["sectors"]))
        hf_changed = list(map(int, ot["hf_tapered_state"])) != list(map(int, nt["hf_tapered_state"]))
        what = ", ".join(([] if not sector_changed else ["wrong sector"])
                         + ([] if not hf_changed else ["wrong HF reference"])) or "regenerated"
        moves.append((old_file, f, new["entry_id"]))
        rows.append("| `%s` | `%s` | %s |" % (old_file.name, f.name, what))

    print("  %d entries to replace" % len(moves))
    for old_file, new_file, eid in moves:
        print("    %s\n      -> %s" % (old_file.name, new_file.name))
    if a.dry_run:
        print("\n  DRY RUN — nothing moved")
        return 0

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for old_file, new_file, _eid in moves:
        shutil.move(str(old_file), str(ARCHIVE / old_file.name))
        shutil.move(str(new_file), str(DB / new_file.name))
    (ARCHIVE / "README.md").write_text(
        README.format(commit=a.commit, table="\n".join(sorted(rows))))
    try:
        REGEN.rmdir()
    except OSError:
        print("  [WARN] %s not empty, left in place" % REGEN)
    print("\n  moved %d superseded entries to %s" % (len(moves), ARCHIVE))
    print("  %d entries now in %s" % (len(list(DB.glob('*.json'))), DB))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
