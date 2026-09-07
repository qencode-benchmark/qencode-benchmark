#!/usr/bin/env python3
"""Compare regenerated entries against the ones they supersede.

    python tools/compare_regenerated.py [--old releases/v4/db] [--new releases/v4/db_regen]

Prints one line per (molecule, mapping, ansatz, reps) configuration: the sector, the
tapered Hartree-Fock state, the constant correction, the energy and the gap, before and
after. Written for the 2026-09-07 Z2 sector fix, where the point is to show exactly what
moved and to make it impossible to claim a change was smaller than it was.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 0.01


def key(entry):
    e = entry["encoding"]
    return (entry["problem"]["name"], e["mapping"], e["ansatz_type"], e["ansatz_reps"],
            entry["problem"]["orbital_optimization"])


def load(d: Path):
    out = {}
    for f in sorted(d.glob("*.json")):
        entry = json.loads(f.read_text())
        out.setdefault(key(entry), []).append((f.name, entry))
    return out


def fmt(v, n=6):
    return "—" if v is None else ("%.*f" % (n, v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=str(ROOT / "releases" / "v4" / "db"))
    ap.add_argument("--new", default=str(ROOT / "releases" / "v4" / "db_regen"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true",
                    help="emit the results table for docs/SECTOR_FIX.md")
    a = ap.parse_args()

    old, new = load(Path(a.old)), load(Path(a.new))
    rows = []
    for k in sorted(set(new) & set(old)):
        (of, oe), = old[k][:1] or [(None, None)]
        (nf, ne), = new[k][:1] or [(None, None)]
        ot, nt = oe["encoding"]["tapering"], ne["encoding"]["tapering"]
        oq, nq = oe["results"]["quality"], ne["results"]["quality"]
        rows.append({
            "molecule": k[0], "mapping": k[1], "ansatz": k[2], "reps": k[3],
            "old_file": of, "new_file": nf,
            "old_sector": ot["sectors"], "new_sector": nt["sectors"],
            "sector_changed": list(map(int, ot["sectors"])) != list(map(int, nt["sectors"])),
            "old_hf": ot["hf_tapered_state"], "new_hf": nt["hf_tapered_state"],
            "hf_changed": list(map(int, ot["hf_tapered_state"])) != list(map(int, nt["hf_tapered_state"])),
            "old_const_corr": ot.get("bk_constant_correction_ha"),
            "new_const_corr": nt.get("bk_constant_correction_ha"),
            "old_qubits": ot["tapered_num_qubits"], "new_qubits": nt["tapered_num_qubits"],
            "old_exact": oe["results"]["reference"]["exact_qubit_ground_energy_hartree"],
            "new_exact": ne["results"]["reference"]["exact_qubit_ground_energy_hartree"],
            "casci": ne["results"]["reference"]["casci_ground_energy_hartree"],
            "old_vqe": oe["results"]["vqe"]["best_energy_hartree"],
            "new_vqe": ne["results"]["vqe"]["best_energy_hartree"],
            "old_gap_mHa": oq["abs_vqe_exact_gap"] * 1e3,
            "new_gap_mHa": nq["abs_vqe_exact_gap"] * 1e3,
            "old_trust": oe["trust"]["level"], "new_trust": ne["trust"]["level"],
        })

    if a.json:
        print(json.dumps(rows, indent=1))
        return 0

    if a.markdown:
        print("| entry | what was wrong | gap before | gap after | trust |")
        print("|---|---|---|---|---|")
        amap = {"hea": "HEA", "uccsd_tapered": "UCCSD", "adapt": "ADAPT"}
        mmap = {"parity": "parity", "bravyi_kitaev": "Bravyi-Kitaev", "jordan_wigner": "JW"}
        for r in sorted(rows, key=lambda r: (r["molecule"], r["mapping"], r["ansatz"], r["reps"])):
            corr = r["old_const_corr"] or 0.0
            what = []
            if abs(corr) > 1e-6:
                what.append("wrong sector, masked by a %.3f Ha correction" % abs(corr))
            elif r["sector_changed"] and r["old_qubits"] != r["new_qubits"]:
                # the sector list changed length because the symmetry count did: a CASSCF
                # gauge effect (see NOISY_TIER.md), not the sector bug
                what.append("symmetry count changed with the CASSCF gauge (%d -> %d qubits)"
                            % (r["old_qubits"], r["new_qubits"]))
            if r["hf_changed"]:
                what.append("wrong Hartree-Fock reference")
            label = "%s %s %s" % (r["molecule"], mmap.get(r["mapping"], r["mapping"]),
                                  amap.get(r["ansatz"], r["ansatz"]))
            if r["ansatz"] == "hea" and r["reps"]:
                label += " r%d" % r["reps"]
            print("| %s | %s | %.4f | %.4f | %s |" % (
                label, "; ".join(what) or "regenerated", r["old_gap_mHa"], r["new_gap_mHa"],
                r["new_trust"] if r["old_trust"] == r["new_trust"] else "%s -> %s" % (r["old_trust"], r["new_trust"])))
        return 0

    print("%-12s %-14s %-6s %-4s %-11s %-11s %10s %10s  %-10s %-10s" %
          ("molecule", "mapping", "ansatz", "reps", "sector", "hf state", "gap_old", "gap_new",
           "trust_old", "trust_new"))
    print("-" * 120)
    for r in rows:
        print("%-12s %-14s %-6s %-4s %-11s %-11s %10.4f %10.4f  %-10s %-10s%s" % (
            r["molecule"], r["mapping"], r["ansatz"][:6], r["reps"],
            "CHANGED" if r["sector_changed"] else "same",
            "CHANGED" if r["hf_changed"] else "same",
            r["old_gap_mHa"], r["new_gap_mHa"], r["old_trust"], r["new_trust"],
            "" if r["old_trust"] == r["new_trust"] else "   <== TRUST CHANGED"))

    print()
    print("  How far the OLD tapered sector's ground state sat above CASCI.")
    print("  The stored exact energy of an old entry already agreed with CASCI -- that is")
    print("  what the constant correction did. Subtracting it back out shows the fault:")
    for r in rows:
        corr = r["old_const_corr"] or 0.0
        unmasked = abs((r["old_exact"] - corr) - r["casci"])
        d_new = abs(r["new_exact"] - r["casci"])
        print("    %-12s %-14s %-6s  before %10.6f Ha %-22s   after %.2e Ha" % (
            r["molecule"], r["mapping"], r["ansatz"][:6], unmasked,
            "(masked by correction)" if corr else "(sector was right)", d_new))

    changed = [r for r in rows if r["old_trust"] != r["new_trust"]]
    print()
    print("  %d configurations compared; %d changed sector, %d changed HF state, %d changed trust level"
          % (len(rows), sum(r["sector_changed"] for r in rows), sum(r["hf_changed"] for r in rows),
             len(changed)))
    for r in changed:
        print("    %s %s %s: %s -> %s (gap %.4f -> %.4f mHa)"
              % (r["molecule"], r["mapping"], r["ansatz"], r["old_trust"], r["new_trust"],
                 r["old_gap_mHa"], r["new_gap_mHa"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
