import { ensureSchema, getEntries, getMetadata } from "./db";

// ─── Shared helpers ───────────────────────────────────────────────────────────

function num(v) {
  if (v === undefined || v === null || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/**
 * UCCSD circuits often report symbolic metrics (depth=1, 2q=1) before
 * transpilation. We detect and nullify them so the UI shows "N/A".
 */
function applySymbolicMetrics(row) {
  const ansatz = String(row.ansatz || "").toLowerCase();
  const depth  = num(row.depth);
  const twoQ   = num(row.two_q_gates ?? row["2q_gates"]);
  const symbolic = ansatz === "uccsd" && ((depth ?? 0) <= 1 || (twoQ ?? 0) <= 1);
  return {
    depth:           symbolic ? null : depth,
    twoQ:            symbolic ? null : twoQ,
    symbolicMetrics: symbolic,
  };
}

// ─── DB loader (production) ───────────────────────────────────────────────────

async function loadFromDatabase() {
  // Auto-create tables on first run — safe to call repeatedly (idempotent).
  await ensureSchema();

  const [accRows, costRows, balancedRows, researchRows, metadata] = await Promise.all([
    getEntries("accuracy"),
    getEntries("cost"),
    getEntries("balanced"),
    getEntries("research"),
    getMetadata(),
  ]);

  // DB exists but hasn't been seeded yet — fall back to CSV so the page renders.
  if (accRows.length === 0 && costRows.length === 0) {
    console.warn("[data] DB is empty — falling back to CSV files");
    return loadFromCsv();
  }

  const normalize = (rows) =>
    rows.map((r) => ({
      rank:               Number(r.rank),
      molecule:           r.molecule,
      mapping:            r.mapping,
      ansatz:             r.ansatz,
      gap:                num(r.gap),
      balancedScore:      num(r.balanced_score),
      baseline:           Boolean(r.baseline),
      beatsClassical:     r.beats_classical === true || r.beats_classical === "true",
      ccsdTCorrelation:   num(r.ccsd_t_correlation),
      vqeEnergy:          num(r.vqe_energy),
      casciEnergy:        num(r.casci_energy),
      hfEnergy:           num(r.hf_energy),
      ...applySymbolicMetrics(r),
    }));

  return {
    acc:      normalize(accRows),
    cost:     normalize(costRows),
    balanced: normalize(balancedRows),
    research: normalize(researchRows),
    metadata,
  };
}

// ─── CSV loader (local dev fallback) ─────────────────────────────────────────

function loadFromCsv() {
  // Dynamic require so Next.js doesn't complain about `fs` in edge environments.
  const fs   = require("node:fs");
  const path = require("node:path");

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length === 0) return [];
    const headers = lines[0].split(",");
    return lines.slice(1).map((line) => {
      const values = line.split(",");
      const row = {};
      headers.forEach((h, i) => { row[h] = values[i]; });
      return row;
    });
  }

  const base = path.join(process.cwd(), "public", "data");

  const normalize = (rows, isBalanced = false) =>
    rows.map((r) => ({
      rank:               num(r.rank),
      molecule:           r.molecule,
      mapping:            r.mapping,
      ansatz:             r.ansatz,
      gap:                num(r.gap),
      balancedScore:      isBalanced ? num(r.balanced_score) : null,
      baseline:           String(r.baseline).toLowerCase() === "true",
      beatsClassical:     String(r.beats_classical).toLowerCase() === "true",
      ccsdTCorrelation:   num(r.ccsd_t_correlation),
      vqeEnergy:          num(r.vqe_energy),
      casciEnergy:        num(r.casci_energy),
      hfEnergy:           num(r.hf_energy),
      ...applySymbolicMetrics({ ...r, two_q_gates: r["2q_gates"] }),
    }));

  const acc      = normalize(parseCsv(fs.readFileSync(path.join(base, "leaderboard_accuracy.csv"),      "utf-8")));
  const cost     = normalize(parseCsv(fs.readFileSync(path.join(base, "leaderboard_hardware_cost.csv"), "utf-8")));
  const balanced = normalize(parseCsv(fs.readFileSync(path.join(base, "leaderboard_balanced.csv"),      "utf-8")), true);
  const metadata = JSON.parse(fs.readFileSync(path.join(base, "leaderboard_metadata.json"), "utf-8"));

  const researchCsvPath = path.join(base, "leaderboard_research.csv");
  const research = fs.existsSync(researchCsvPath)
    ? normalize(parseCsv(fs.readFileSync(researchCsvPath, "utf-8")))
    : [];

  return { acc, cost, balanced, research, metadata };
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Load leaderboard data.
 * - Production (POSTGRES_URL set): fetches live from Neon Postgres
 * - Local dev (no POSTGRES_URL): reads static CSV files from public/data/
 */
export async function loadLeaderboardData() {
  if (process.env.POSTGRES_URL) {
    return loadFromDatabase();
  }
  // Synchronous CSV path wrapped in a resolved promise for a uniform interface
  return Promise.resolve(loadFromCsv());
}
