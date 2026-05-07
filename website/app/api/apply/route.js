import { sendApplyConfirmation, sendApplyAdminNotification } from "@/lib/email";

/**
 * POST /api/apply
 *
 * Receives the access application form, validates it, and fires two emails:
 *  1. Confirmation to the applicant
 *  2. Full details to admin for review
 *
 * Body (JSON): all fields from the apply form
 */

const REQUIRED = ["company", "contactName", "workEmail", "moleculeScope", "timeline"];

function deriveRecommendation(monthlyRuns) {
  const n = Number(monthlyRuns || 0);
  if (n >= 40) return "Enterprise";
  if (n >= 10) return "Team";
  return "Starter";
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(email || ""));
}

export async function POST(request) {
  // ── 1. Parse body ──────────────────────────────────────────────────────────
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  // ── 2. Validate required fields ────────────────────────────────────────────
  const missing = REQUIRED.filter((k) => !String(body[k] || "").trim());
  if (missing.length > 0) {
    return Response.json(
      { error: `Missing required fields: ${missing.join(", ")}` },
      { status: 422 }
    );
  }

  if (!isValidEmail(body.workEmail)) {
    return Response.json({ error: "Invalid work email address" }, { status: 422 });
  }

  // ── 3. Build full fields object ────────────────────────────────────────────
  const fields = {
    company:               String(body.company        || "").trim(),
    contactName:           String(body.contactName    || "").trim(),
    workEmail:             String(body.workEmail      || "").trim().toLowerCase(),
    role:                  String(body.role           || "").trim(),
    moleculeScope:         String(body.moleculeScope  || "").trim(),
    timeline:              String(body.timeline       || "").trim(),
    monthlyRuns:           String(body.monthlyRuns    || "").trim(),
    needsCertification:    String(body.needsCertification    || "yes"),
    needsPrivateBenchmark: String(body.needsPrivateBenchmark || "yes"),
    notes:                 String(body.notes          || "").trim(),
    recommendation:        deriveRecommendation(body.monthlyRuns),
  };

  // ── 4. Send emails ─────────────────────────────────────────────────────────
  const [confirmResult, adminResult] = await Promise.allSettled([
    sendApplyConfirmation(fields),
    sendApplyAdminNotification(fields),
  ]);

  if (confirmResult.status === "rejected") {
    console.error("[apply] Failed to send confirmation email:", confirmResult.reason);
  } else if (confirmResult.value?.error) {
    console.error("[apply] Resend error (confirmation):", confirmResult.value.error);
  }

  if (adminResult.status === "rejected") {
    console.error("[apply] Failed to send admin notification:", adminResult.reason);
  } else if (adminResult.value?.error) {
    console.error("[apply] Resend error (admin):", adminResult.value.error);
  }

  // Return success even if email failed — we logged it and don't want to alarm the applicant.
  // In production, Vercel logs will capture any Resend failures for follow-up.
  console.log(`[apply] Application submitted — ${fields.company} <${fields.workEmail}> — ${fields.recommendation}`);

  return Response.json({ ok: true, recommendation: fields.recommendation });
}

export async function GET() {
  return Response.json({ error: "Method Not Allowed" }, { status: 405 });
}
