import { revalidatePath } from "next/cache";
import { ensureSchema, replaceEntries, upsertMetadata } from "@/lib/db";

/**
 * POST /api/admin/publish-leaderboard
 *
 * Replaces all leaderboard entries in Postgres and busts the /leaderboard cache.
 * Called from the Ubuntu pipeline after a new certified run completes.
 *
 * Auth: Authorization: Bearer <LEADERBOARD_PUBLISH_SECRET>
 *
 * Body (JSON):
 * {
 *   "accuracy": [
 *     { "rank": 1, "molecule": "BeH2", "mapping": "parity", "ansatz": "uccsd",
 *       "gap": 0.003576, "depth": 1749, "two_q_gates": 1276, "baseline": false }
 *   ],
 *   "cost":     [ ... same shape ... ],
 *   "balanced": [ ... same shape + "balanced_score": 0.197 ... ],
 *   "metadata": {
 *     "suite_version": "v2",
 *     "leaderboard_rules": "v1",
 *     "generation_date": "2026-04-23",
 *     "entries_included": 17,
 *     "trust_filter": "certified_only"
 *   }
 * }
 *
 * Required env vars:
 *   POSTGRES_URL               — Neon connection string (set by Vercel integration)
 *   LEADERBOARD_PUBLISH_SECRET — shared secret for bearer auth
 */
export async function POST(request) {
  // ── 1. Auth ────────────────────────────────────────────────────────────────
  const secret = process.env.LEADERBOARD_PUBLISH_SECRET;
  if (!secret) {
    console.error("[publish-leaderboard] LEADERBOARD_PUBLISH_SECRET is not configured");
    return Response.json({ error: "Server misconfiguration" }, { status: 500 });
  }

  const authHeader = request.headers.get("authorization") ?? "";
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : null;
  if (token !== secret) {
    console.warn("[publish-leaderboard] Unauthorized request — bad token");
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  // ── 2. Parse body ──────────────────────────────────────────────────────────
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { accuracy, cost, balanced, metadata } = body ?? {};

  if (!Array.isArray(accuracy) || !Array.isArray(cost) || !Array.isArray(balanced)) {
    return Response.json(
      { error: "Body must include accuracy, cost, and balanced arrays" },
      { status: 422 }
    );
  }

  // ── 3. Validate entry shape ────────────────────────────────────────────────
  const requiredFields = ["rank", "molecule", "mapping", "ansatz"];
  for (const [label, entries] of [["accuracy", accuracy], ["cost", cost], ["balanced", balanced]]) {
    for (const entry of entries) {
      for (const field of requiredFields) {
        if (entry[field] === undefined || entry[field] === null) {
          return Response.json(
            { error: `Entry in '${label}' is missing required field: ${field}` },
            { status: 422 }
          );
        }
      }
    }
  }

  // ── 4. Write to database ───────────────────────────────────────────────────
  try {
    await ensureSchema();

    const [accCount, costCount, balancedCount] = await Promise.all([
      replaceEntries("accuracy", accuracy).then(() => accuracy.length),
      replaceEntries("cost",     cost).then(()     => cost.length),
      replaceEntries("balanced", balanced).then(() => balanced.length),
    ]);

    if (metadata && typeof metadata === "object") {
      await upsertMetadata(metadata);
    }

    console.log(
      `[publish-leaderboard] Published — accuracy:${accCount} cost:${costCount} balanced:${balancedCount}`
    );
  } catch (err) {
    console.error("[publish-leaderboard] Database write failed:", err);
    return Response.json({ error: "Database write failed", detail: err.message }, { status: 500 });
  }

  // ── 5. Bust leaderboard page cache ────────────────────────────────────────
  try {
    revalidatePath("/leaderboard");
    console.log("[publish-leaderboard] Revalidated /leaderboard");
  } catch (err) {
    // Non-fatal — the hourly revalidation will catch it
    console.warn("[publish-leaderboard] revalidatePath failed:", err.message);
  }

  return Response.json({
    ok: true,
    published: {
      accuracy: accuracy.length,
      cost:     cost.length,
      balanced: balanced.length,
    },
  });
}

export async function GET() {
  return Response.json({ error: "Method Not Allowed" }, { status: 405 });
}
