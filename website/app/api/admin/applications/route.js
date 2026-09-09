import { ensureSchema, listApplications } from "@/lib/db";

/**
 * Admin applications API.
 * Requires: Authorization: Bearer <LEADERBOARD_PUBLISH_SECRET>
 *
 * GET /api/admin/applications?limit=100 — newest access applications first
 *
 * Exists because the application email is a notification, not the record. If mail
 * breaks again, this endpoint still answers the only question that matters: who
 * applied, and did we ever tell anyone about it (email_status).
 */

function authorized(request) {
  const secret = (process.env.LEADERBOARD_PUBLISH_SECRET ?? "").trim();
  if (!secret) return false;
  const header = request.headers.get("authorization") ?? "";
  return header === `Bearer ${secret}`;
}

export async function GET(request) {
  if (!authorized(request)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    await ensureSchema();
    const limit = Number(new URL(request.url).searchParams.get("limit")) || 100;
    const applications = await listApplications(limit);
    const unnotified = applications.filter((a) => a.email_status !== "sent").length;
    return Response.json({ count: applications.length, unnotified, applications });
  } catch (err) {
    console.error("[applications] GET failed:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
