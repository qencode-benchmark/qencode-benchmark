import { finishJob } from "@/lib/db";

/**
 * POST /api/admin/jobs/[id]
 *
 * Mark a job as completed or failed.
 * Called by the Ubuntu poller after a benchmark run finishes.
 *
 * Body: { "success": true|false, "error_message": "...", "notes": "..." }
 */

function authorized(request) {
  const secret = (process.env.LEADERBOARD_PUBLISH_SECRET ?? "").trim();
  if (!secret) return false;
  const header = request.headers.get("authorization") ?? "";
  return header === `Bearer ${secret}`;
}

export async function POST(request, { params }) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id: rawId } = await params;
  const id = Number(rawId);
  if (!id || isNaN(id)) {
    return Response.json({ error: "Invalid job id" }, { status: 400 });
  }

  let body = {};
  try { body = await request.json(); } catch { /* no body defaults to success */ }

  const success      = body.success !== false; // default true
  const errorMessage = body.error_message ?? null;
  const notes        = body.notes ?? null;

  try {
    const order = await finishJob(id, { success, errorMessage, notes });
    const certToken = order?.certification_token ?? null;
    console.log(`[jobs] Job #${id} marked as ${success ? "completed" : "failed"}${certToken ? ` — cert token: ${certToken}` : ""}`);
    return Response.json({
      ok: true,
      id,
      status: success ? "completed" : "failed",
      certification_token: certToken,
      verify_url: certToken
        ? `https://www.qencode-benchmark.org/verify/${certToken}`
        : null,
    });
  } catch (err) {
    console.error(`[jobs] finishJob #${id} failed:`, err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
