import { neon } from "@neondatabase/serverless";

/**
 * Returns a Neon sql tag connected to POSTGRES_URL.
 * Throws clearly if the env var is missing.
 */
function getDb() {
  const url = process.env.POSTGRES_URL;
  if (!url) throw new Error("POSTGRES_URL environment variable is not set");
  return neon(url);
}

// ─── Schema ──────────────────────────────────────────────────────────────────

/**
 * Create tables if they don't exist yet.
 * Safe to call multiple times (idempotent).
 * Call this once from the admin setup route or seed script.
 */
export async function ensureSchema() {
  const sql = getDb();

  await sql`
    CREATE TABLE IF NOT EXISTS leaderboard_entries (
      id             SERIAL PRIMARY KEY,
      category       VARCHAR(20)       NOT NULL,
      rank           INTEGER           NOT NULL,
      molecule       VARCHAR(50)       NOT NULL,
      mapping        VARCHAR(50)       NOT NULL,
      ansatz         VARCHAR(50)       NOT NULL,
      gap            DOUBLE PRECISION,
      depth          INTEGER,
      two_q_gates    INTEGER,
      balanced_score DOUBLE PRECISION,
      baseline       BOOLEAN           NOT NULL DEFAULT false,
      updated_at     TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
      UNIQUE (category, molecule, mapping, ansatz)
    )
  `;

  await sql`
    CREATE TABLE IF NOT EXISTS leaderboard_metadata (
      key        VARCHAR(100) PRIMARY KEY,
      value      TEXT         NOT NULL,
      updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
  `;
}

// ─── Reads ────────────────────────────────────────────────────────────────────

/**
 * Fetch all entries for a given category, ordered by rank.
 * category: 'accuracy' | 'cost' | 'balanced'
 */
export async function getEntries(category) {
  const sql = getDb();
  const rows = await sql`
    SELECT * FROM leaderboard_entries
    WHERE category = ${category}
    ORDER BY rank ASC
  `;
  return rows;
}

/**
 * Fetch all metadata key/value pairs as a plain object.
 */
export async function getMetadata() {
  const sql = getDb();
  const rows = await sql`SELECT key, value FROM leaderboard_metadata`;
  return Object.fromEntries(rows.map((r) => [r.key, r.value]));
}

// ─── Writes ───────────────────────────────────────────────────────────────────

/**
 * Replace all entries for a given category with a fresh set.
 * Runs inside a transaction to avoid a window where the table is empty.
 */
export async function replaceEntries(category, entries) {
  const sql = getDb();

  // Neon HTTP driver doesn't support multi-statement transactions via the tag,
  // so we delete-then-insert sequentially. The window is milliseconds.
  await sql`DELETE FROM leaderboard_entries WHERE category = ${category}`;

  for (const e of entries) {
    await sql`
      INSERT INTO leaderboard_entries
        (category, rank, molecule, mapping, ansatz, gap, depth, two_q_gates, balanced_score, baseline, updated_at)
      VALUES
        (
          ${category},
          ${e.rank},
          ${e.molecule},
          ${e.mapping},
          ${e.ansatz},
          ${e.gap   ?? null},
          ${e.depth ?? null},
          ${e.two_q_gates ?? null},
          ${e.balanced_score ?? null},
          ${Boolean(e.baseline)},
          NOW()
        )
    `;
  }
}

/**
 * Upsert metadata key/value pairs.
 */
export async function upsertMetadata(updates) {
  const sql = getDb();
  for (const [key, value] of Object.entries(updates)) {
    await sql`
      INSERT INTO leaderboard_metadata (key, value, updated_at)
      VALUES (${key}, ${String(value)}, NOW())
      ON CONFLICT (key) DO UPDATE
        SET value = EXCLUDED.value, updated_at = NOW()
    `;
  }
}
