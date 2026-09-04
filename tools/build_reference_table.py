#!/usr/bin/env python
"""Generate the packaged reference table that qencode.score reads.

Scoring somebody else's VQE energy needs one thing this project already has and they
probably do not: the exact ground state of the same active-space Hamiltonian. Running
CASCI to get it costs a PySCF install and a wait; looking it up costs nothing. So the
references are extracted from the published database into a small JSON file that ships
inside the wheel, which is what lets `pip install qencode-benchmark` score a result with
no chemistry stack present.

The table is safe to build this way because the reference is a property of the PROBLEM,
not of the run. Measured across all 54 published entries: for every
(molecule, basis, active space, orbital treatment) the recorded reference energy is
identical to the last digit across every mapping and every ansatz -- spread 0.0 Ha, 16
distinct configurations. If that ever stops being true the table is not well defined, so
this refuses to write rather than pick one.

    python tools/build_reference_table.py            # write src/qencode/data/references_v4.json
    python tools/build_reference_table.py --check    # exit 1 if the file is out of date

tests/test_score.py calls build() directly and compares, so the file cannot drift from
the database without a test failing.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DB = REPO / "releases" / "v4" / "db"
OUT = REPO / "src" / "qencode" / "data" / "references_v4.json"

CERT_THRESHOLD_HA = 0.01
CHEMICAL_ACCURACY_HA = 1.6e-3

# The reference must be identical across every encoding of the same problem. This is the
# tolerance for calling two recorded values the same number; measured spread is 0.0.
REFERENCE_AGREEMENT_HA = 1e-9


def _key(d):
    p = d["problem"]
    a = p["active_space"]
    return (p["name"], p["basis"], int(a["num_electrons"]),
            int(a["num_spatial_orbitals"]), p.get("orbital_optimization") or "hf")


def build(db_dir=DEFAULT_DB) -> dict:
    """Return the reference table as a dict. Pure function of the entry database."""
    files = sorted(glob.glob(os.path.join(str(db_dir), "*.json")))
    if not files:
        raise SystemExit("no entries found in %s" % db_dir)

    refs, entries = {}, []
    for f in files:
        d = json.load(open(f, encoding="utf-8"))
        p, r = d["problem"], d["results"]["reference"]
        cc = d["results"].get("classical_comparison") or {}
        q = d["results"]["quality"]
        k = _key(d)

        row = {
            "molecule": k[0],
            "basis": k[1],
            "geometry": p.get("geometry"),
            "charge": p.get("charge", 0),
            "spin": p.get("spin", 0),
            "active_electrons": k[2],
            "active_orbitals": k[3],
            "orbital_optimization": k[4],
            "casci_ground_energy_hartree": r["casci_ground_energy_hartree"],
            "exact_qubit_ground_energy_hartree": r["exact_qubit_ground_energy_hartree"],
            "hf_energy_hartree": cc.get("hf_energy_hartree"),
            "ccsd_t_energy_hartree": cc.get("ccsd_t_energy_hartree"),
            "ccsd_t_correlation": cc.get("ccsd_t_correlation"),
        }
        if k in refs:
            prev = refs[k]
            for field in ("exact_qubit_ground_energy_hartree", "casci_ground_energy_hartree"):
                a, b = prev[field], row[field]
                if a is not None and b is not None and abs(a - b) > REFERENCE_AGREEMENT_HA:
                    raise SystemExit(
                        "reference disagrees across encodings of the same problem: %s %s "
                        "%.12f vs %.12f. The table would have to pick one, so it is not "
                        "well defined and nothing is written." % (k, field, a, b))
        else:
            refs[k] = row

        entries.append({
            "molecule": k[0],
            "orbital_optimization": k[4],
            "mapping": d["encoding"]["mapping"],
            "ansatz": d["encoding"]["ansatz_type"],
            "optimizer": (d.get("run_config") or {}).get("optimizer"),
            "gap_ha": q["abs_vqe_exact_gap"],
            "entry_id": d.get("entry_id"),
        })

    for row in refs.values():
        row["n_published_entries"] = sum(
            1 for e in entries
            if e["molecule"] == row["molecule"]
            and e["orbital_optimization"] == row["orbital_optimization"])

    return {
        "schema": "qencode-references/1",
        "suite_version": "4",
        "default_basis": "cc-pvdz",
        "certification_threshold_ha": CERT_THRESHOLD_HA,
        "chemical_accuracy_ha": CHEMICAL_ACCURACY_HA,
        "gap_reference": "exact_qubit_hamiltonian",
        "source": "releases/v4/db",
        "n_source_entries": len(entries),
        # No timestamp on purpose: the file is a pure function of the database, so
        # regenerating it produces no diff unless the data changed, and the test can
        # compare byte for byte.
        "references": [refs[k] for k in sorted(refs)],
        "entries": sorted(entries, key=lambda e: (e["molecule"], e["gap_ha"])),
    }


def serialise(table: dict) -> str:
    return json.dumps(table, indent=1, sort_keys=False, ensure_ascii=True) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db-dir", default=str(DEFAULT_DB))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--check", action="store_true",
                    help="verify the file matches the database; write nothing")
    args = ap.parse_args()

    text = serialise(build(Path(args.db_dir)))
    out = Path(args.out)

    if args.check:
        if not out.exists():
            print("MISSING: %s" % out)
            return 1
        if out.read_text(encoding="utf-8") != text:
            print("STALE: %s does not match %s" % (out, args.db_dir))
            print("       run: python tools/build_reference_table.py")
            return 1
        print("up to date: %s" % out)
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    table = json.loads(text)
    print("wrote %s" % out)
    print("  %d references from %d entries, %.1f KB"
          % (len(table["references"]), table["n_source_entries"], len(text) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
