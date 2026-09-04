import fs from "node:fs";
import path from "node:path";

/**
 * The QEncode reference table — the exact ground-state energies `qencode.score`
 * compares a user's VQE energy against.
 *
 * This is a byte-for-byte copy of src/qencode/data/references_v4.json, the table that
 * ships inside the Python package. It is duplicated here rather than imported because
 * that file lives outside the Next.js project root and would not be traced into the
 * serverless bundle. tests/test_website_references.py fails if the two ever differ, so
 * the site cannot quote a reference energy the package does not agree with.
 *
 * Regenerate both with:  python tools/build_reference_table.py
 */
let _table = null;

export function referencesTable() {
  if (_table === null) {
    const p = path.join(process.cwd(), "public", "data", "references_v4.json");
    _table = JSON.parse(fs.readFileSync(p, "utf-8"));
  }
  return _table;
}

/** One row per scorable problem, sorted by qubit-count proxy then name. */
export function scorableMolecules() {
  const t = referencesTable();
  return t.references
    .map((r) => ({
      molecule: r.molecule,
      basis: r.basis,
      activeElectrons: r.active_electrons,
      activeOrbitals: r.active_orbitals,
      orbitalOptimization: r.orbital_optimization,
      geometry: r.geometry,
      exactEnergy: r.exact_qubit_ground_energy_hartree,
      publishedEntries: r.n_published_entries,
    }))
    .sort((a, b) =>
      a.activeOrbitals - b.activeOrbitals || a.molecule.localeCompare(b.molecule));
}

export function referenceStats() {
  const t = referencesTable();
  return {
    molecules: t.references.length,
    sourceEntries: t.n_source_entries,
    certThresholdHa: t.certification_threshold_ha,
    chemAccuracyHa: t.chemical_accuracy_ha,
    defaultBasis: t.default_basis,
  };
}
