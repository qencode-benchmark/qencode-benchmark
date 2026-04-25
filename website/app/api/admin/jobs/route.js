import { ensureSchema, listActiveJobs, claimNextJob } from "@/lib/db";

/**
 * Admin jobs API — used by the Ubuntu job poller.
 * All endpoints require: Authorization: Bearer <LEADERBOARD_PUBLISH_SECRET>
 *
 * GET  /api/admin/jobs        — list pending + running jobs
 * POST /api/admin/jobs/claim  — atomically claim the oldest pending job
 */

function authorized(request) {
  const secret = process.env.LEADERBOARD_PUBLISH_SECRET;
  if (!secret) return false;
  const header = request.headers.get("authorization") ?? "";
  return header === `Bearer ${secret}`;
}

// ── GET — list active jobs ────────────────────────────────────────────────────
export async function GET(request) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    await ensureSchema();
    const jobs = await listActiveJobs();
    return Response.json({ jobs });
  } catch (err) {
    console.error("[jobs] GET failed:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}

// ── POST — claim next pending job ─────────────────────────────────────────────
export async function POST(request) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body = {};
  try { body = await request.json(); } catch { /* no body is fine */ }

  // Route sub-actions via ?action= query param or body.action
  const url = new URL(request.url);
  const action = url.searchParams.get("action") ?? body.action ?? "claim";

  if (action !== "claim") {
    return Response.json({ error: `Unknown action: ${action}` }, { status: 400 });
  }

  try {
    await ensureSchema();
    const job = await claimNextJob();
    if (!job) {
      return Response.json({ job: null, message: "No pending jobs" });
    }
    console.log(`[jobs] Claimed job #${job.id} — ${job.product_type} for ${job.customer_email}`);
    return Response.json({ job });
  } catch (err) {
    console.error("[jobs] claim failed:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
