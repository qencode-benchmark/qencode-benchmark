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
 * Create leaderboard + orders tables if they don't exist yet. Idempotent.
 */
export async function ensureSchema() {
  const sql = getDb();

  await sql`
    CREATE TABLE IF NOT EXISTS leaderboard_entries (
      id               SERIAL PRIMARY KEY,
      category         VARCHAR(20)       NOT NULL,
      rank             INTEGER           NOT NULL,
      molecule         VARCHAR(50)       NOT NULL,
      mapping          VARCHAR(50)       NOT NULL,
      ansatz           VARCHAR(50)       NOT NULL,
      entry_id         VARCHAR(200),
      gap              DOUBLE PRECISION,
      depth            INTEGER,
      two_q_gates      INTEGER,
      balanced_score      DOUBLE PRECISION,
      baseline            BOOLEAN           NOT NULL DEFAULT false,
      beats_classical     BOOLEAN,
      ccsd_t_correlation  DOUBLE PRECISION,
      vqe_energy          DOUBLE PRECISION,
      casci_energy        DOUBLE PRECISION,
      hf_energy           DOUBLE PRECISION,
      updated_at          TIMESTAMPTZ       NOT NULL DEFAULT NOW(),
      UNIQUE (category, molecule, mapping, ansatz)
    )
  `;

  // Migrate existing tables: add beats_classical if upgrading from older schema
  await sql`
    ALTER TABLE leaderboard_entries
    ADD COLUMN IF NOT EXISTS beats_classical BOOLEAN
  `;

  // Phase 7: classical comparison columns
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS ccsd_t_correlation DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS vqe_energy         DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS casci_energy       DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS hf_energy          DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS entry_id           VARCHAR(200)`;

  // v4 migration: basis set and orbital optimisation method
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS basis       VARCHAR(50)`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS orbital_opt VARCHAR(20)`;

  // Fault-tolerant resource columns: T-gate estimate and non-Clifford gate count.
  // Recorded per entry since v4; surfaced so an entry reads as a resource estimate,
  // not only an accuracy figure.
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS t_gate_estimate    BIGINT`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS non_clifford_gates BIGINT`;

  // Certification margin and fragility (2026-09-04). Two entries certified at 9.98 and
  // 0.001 mHa are both "certified" and only one survives being re-run on another
  // machine; the leaderboard had been showing them identically. margin = 0.01 - gap.
  // amplifies / at_risk come from tools/certification_margin.py; robustness is the
  // measured cross-environment outcome where one exists ('robust' | 'marginal' | 'fragile').
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS optimizer        VARCHAR(50)`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS optimiser_family VARCHAR(20)`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS amplifies        BOOLEAN`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS margin           DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS chem_accurate    BOOLEAN`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS robustness       VARCHAR(20)`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS at_risk          BOOLEAN`;
  // Hardware-penalty track (2026-09-04). The energy of the same circuit under a named
  // gate-noise model, measured by density-matrix simulation (tools/noisy_tier.py).
  // Reported next to the certified gap; not a certification criterion. Values in Ha.
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS noise_status     VARCHAR(24)`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS noise_penalty    DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS noisy_gap        DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS zne_residual     DOUBLE PRECISION`;
  await sql`ALTER TABLE leaderboard_entries ADD COLUMN IF NOT EXISTS noise_model      VARCHAR(40)`;

  await sql`
    CREATE TABLE IF NOT EXISTS leaderboard_metadata (
      key        VARCHAR(100) PRIMARY KEY,
      value      TEXT         NOT NULL,
      updated_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
  `;

  await sql`
    CREATE TABLE IF NOT EXISTS orders (
      id                  SERIAL PRIMARY KEY,
      ls_order_id         VARCHAR(50)  UNIQUE NOT NULL,
      ls_order_number     INTEGER      NOT NULL,
      customer_email      VARCHAR(255) NOT NULL,
      customer_name       VARCHAR(255),
      product_label       VARCHAR(100) NOT NULL,
      product_type        VARCHAR(20)  NOT NULL,
      total_formatted     VARCHAR(20),
      status              VARCHAR(20)  NOT NULL DEFAULT 'pending',
      created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
      started_at          TIMESTAMPTZ,
      completed_at        TIMESTAMPTZ,
      error_message       TEXT,
      notes               TEXT,
      certification_token UUID         UNIQUE
    )
  `;

  // Add certification_token column if upgrading from older schema
  await sql`
    ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS certification_token UUID UNIQUE
  `;

  // Access applications. Added 2026-09-09 because /api/apply used to send two emails
  // and store nothing: a failed send lost the application with no record anywhere, and
  // the applicant still saw a success screen. The row is now the record of truth and
  // the email is a notification about it.
  await sql`
    CREATE TABLE IF NOT EXISTS applications (
      id                      SERIAL PRIMARY KEY,
      company                 VARCHAR(255) NOT NULL,
      contact_name            VARCHAR(255) NOT NULL,
      work_email              VARCHAR(255) NOT NULL,
      role                    VARCHAR(255),
      molecule_scope          TEXT         NOT NULL,
      timeline                VARCHAR(255) NOT NULL,
      monthly_runs            VARCHAR(50),
      needs_certification     VARCHAR(10),
      needs_private_benchmark VARCHAR(10),
      notes                   TEXT,
      recommendation          VARCHAR(50),
      email_status            VARCHAR(20)  NOT NULL DEFAULT 'pending',
      email_error             TEXT,
      created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    )
  `;
}

// ─── Applications ─────────────────────────────────────────────────────────────

/**
 * Record an access application. Returns the new row id.
 *
 * Called before any email is attempted, so that a mail outage cannot lose an
 * application. email_status is updated afterwards with what actually happened.
 */
export async function insertApplication(fields) {
  const sql = getDb();
  const rows = await sql`
    INSERT INTO applications
      (company, contact_name, work_email, role, molecule_scope, timeline,
       monthly_runs, needs_certification, needs_private_benchmark, notes,
       recommendation, email_status)
    VALUES
      (${fields.company}, ${fields.contactName}, ${fields.workEmail},
       ${fields.role || null}, ${fields.moleculeScope}, ${fields.timeline},
       ${fields.monthlyRuns || null}, ${fields.needsCertification || null},
       ${fields.needsPrivateBenchmark || null}, ${fields.notes || null},
       ${fields.recommendation || null}, 'pending')
    RETURNING id
  `;
  return rows[0]?.id ?? null;
}

/** Record what happened to the notification emails for one application. */
export async function markApplicationEmail(id, status, errorMessage) {
  if (!id) return;
  const sql = getDb();
  await sql`
    UPDATE applications
    SET email_status = ${status},
        email_error  = ${errorMessage ? String(errorMessage).slice(0, 2000) : null}
    WHERE id = ${id}
  `;
}

/**
 * Delete one application by id. Returns the deleted row, or null if there was none.
 *
 * For removing a test submission or an obvious junk one. It returns what it deleted so
 * the caller can show what was removed rather than reporting a bare count.
 */
export async function deleteApplication(id) {
  const sql = getDb();
  const rows = await sql`
    DELETE FROM applications WHERE id = ${Number(id)}
    RETURNING id, company, work_email, created_at
  `;
  return rows[0] ?? null;
}

/** Newest applications first. */
export async function listApplications(limit = 100) {
  const sql = getDb();
  return await sql`
    SELECT id, company, contact_name, work_email, role, molecule_scope, timeline,
           monthly_runs, needs_certification, needs_private_benchmark, notes,
           recommendation, email_status, email_error, created_at
    FROM applications
    ORDER BY created_at DESC
    LIMIT ${Math.min(Number(limit) || 100, 500)}
  `;
}

// ─── Orders ───────────────────────────────────────────────────────────────────

/** Insert a new order row when a payment is confirmed. Ignores duplicates. */
export async function insertOrder({ lsOrderId, lsOrderNumber, customerEmail, customerName, productLabel, productType, totalFormatted }) {
  const sql = getDb();
  await sql`
    INSERT INTO orders
      (ls_order_id, ls_order_number, customer_email, customer_name,
       product_label, product_type, total_formatted, status, created_at)
    VALUES
      (${String(lsOrderId)}, ${Number(lsOrderNumber)}, ${customerEmail},
       ${customerName || null}, ${productLabel}, ${productType},
       ${totalFormatted || null}, 'pending', NOW())
    ON CONFLICT (ls_order_id) DO NOTHING
  `;
}

/** Claim the oldest pending order — mark it running and return it. Returns null if queue is empty. */
export async function claimNextJob() {
  const sql = getDb();
  const rows = await sql`
    UPDATE orders
    SET    status = 'running', started_at = NOW()
    WHERE  id = (
      SELECT id FROM orders
      WHERE  status = 'pending'
      ORDER  BY created_at ASC
      LIMIT  1
    )
    RETURNING *
  `;
  return rows[0] ?? null;
}

/** Mark a job as completed or failed. Returns the updated row (includes certification_token). */
export async function finishJob(id, { success, errorMessage, notes }) {
  const sql = getDb();
  const rows = await sql`
    UPDATE orders
    SET
      status              = ${success ? "completed" : "failed"},
      completed_at        = NOW(),
      error_message       = ${errorMessage || null},
      notes               = ${notes || null},
      certification_token = CASE
        WHEN ${success} = true AND certification_token IS NULL
        THEN gen_random_uuid()
        ELSE certification_token
      END
    WHERE id = ${Number(id)}
    RETURNING *
  `;
  return rows[0] ?? null;
}

/**
 * Look up a certification by its public token.
 * Returns only public-safe fields — no customer email exposed.
 */
export async function getCertificationByToken(token) {
  const sql = getDb();
  const rows = await sql`
    SELECT
      certification_token,
      ls_order_number,
      product_label,
      product_type,
      status,
      created_at,
      completed_at,
      notes,
      customer_name
    FROM orders
    WHERE certification_token = ${token}
      AND status = 'completed'
  `;
  return rows[0] ?? null;
}

/** Fetch all orders for a given customer email, newest first. */
export async function getOrdersByEmail(email) {
  const sql = getDb();
  return sql`
    SELECT * FROM orders
    WHERE  customer_email = ${email}
    ORDER  BY created_at DESC
  `;
}

/** List all non-completed jobs (for the admin API). */
/**
 * Every order, newest first. listActiveJobs answers "what is the queue doing"; this
 * answers "who has ever bought something", which is the question you need after an
 * outbound-mail outage, when an order may have been fulfilled while its confirmation
 * email failed.
 */
export async function listAllOrders(limit = 200) {
  const sql = getDb();
  return sql`
    SELECT id, ls_order_number, customer_email, customer_name, product_label,
           status, created_at, completed_at, error_message
    FROM   orders
    ORDER  BY created_at DESC
    LIMIT  ${Math.min(Number(limit) || 200, 1000)}
  `;
}

export async function listActiveJobs() {
  const sql = getDb();
  return sql`
    SELECT * FROM orders
    WHERE  status IN ('pending', 'running')
    ORDER  BY created_at ASC
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
        (category, rank, molecule, mapping, ansatz, entry_id, gap, depth, two_q_gates, balanced_score,
         baseline, beats_classical, ccsd_t_correlation, vqe_energy, casci_energy, hf_energy,
         basis, orbital_opt, t_gate_estimate, non_clifford_gates,
         optimizer, optimiser_family, amplifies, margin, chem_accurate, robustness, at_risk,
         noise_status, noise_penalty, noisy_gap, zne_residual, noise_model,
         updated_at)
      VALUES
        (
          ${category},
          ${e.rank},
          ${e.molecule},
          ${e.mapping},
          ${e.ansatz},
          ${e.entry_id ?? null},
          ${e.gap   ?? null},
          ${e.depth ?? null},
          ${e.two_q_gates ?? null},
          ${e.balanced_score ?? null},
          ${Boolean(e.baseline)},
          ${e.beats_classical ?? null},
          ${e.ccsd_t_correlation ?? null},
          ${e.vqe_energy         ?? null},
          ${e.casci_energy       ?? null},
          ${e.hf_energy          ?? null},
          ${e.basis              ?? null},
          ${e.orbital_opt        ?? null},
          ${e.t_gate_estimate    ?? null},
          ${e.non_clifford_gates ?? null},
          ${e.optimizer          ?? null},
          ${e.optimiser_family   ?? null},
          ${e.amplifies          ?? null},
          ${e.margin             ?? null},
          ${e.chem_accurate      ?? null},
          ${e.robustness         ?? null},
          ${e.at_risk            ?? null},
          ${e.noise_status       ?? null},
          ${e.noise_penalty      ?? null},
          ${e.noisy_gap          ?? null},
          ${e.zne_residual       ?? null},
          ${e.noise_model        ?? null},
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
