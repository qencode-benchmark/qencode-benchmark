import { sendApplyConfirmation, sendApplyAdminNotification } from "@/lib/email";
import { ensureSchema, insertApplication, markApplicationEmail } from "@/lib/db";

/**
 * POST /api/apply
 *
 * Receives the access application form, validates it, writes it to the database, and
 * then sends two emails: a confirmation to the applicant and the full details to the
 * admin address.
 *
 * The order matters. Until 2026-09-09 this route only sent the two emails and stored
 * nothing, so a mail outage lost the application completely while still showing the
 * applicant a success screen. Outbound mail had in fact been dead for some time, which
 * is how that was found. The database row is now the record; the email is a
 * notification about the row, and its outcome is recorded on the row itself.
 *
 * If neither the row nor a single email survives, the response says so rather than
 * claiming success, because at that point nothing anywhere has the application.
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

  // ── 4. Store it, before anything that can fail silently ────────────────────
  let applicationId = null;
  let storeError = null;
  try {
    await ensureSchema();
    applicationId = await insertApplication(fields);
    console.log(`[apply] stored application ${applicationId} — ${fields.company}`);
  } catch (err) {
    storeError = err;
    console.error("[apply] FAILED TO STORE APPLICATION:", err);
  }

  // ── 5. Send emails ─────────────────────────────────────────────────────────
  const [confirmResult, adminResult] = await Promise.allSettled([
    sendApplyConfirmation(fields),
    sendApplyAdminNotification(fields),
  ]);

  function failureOf(result, label) {
    if (result.status === "rejected") {
      console.error(`[apply] Failed to send ${label} email:`, result.reason);
      return String(result.reason?.message || result.reason);
    }
    if (result.value?.error) {
      console.error(`[apply] Resend error (${label}):`, result.value.error);
      return String(result.value.error?.message || JSON.stringify(result.value.error));
    }
    return null;
  }

  const confirmFailure = failureOf(confirmResult, "confirmation");
  const adminFailure = failureOf(adminResult, "admin");

  // The admin notification is the one that decides whether a human learns about this.
  const emailStatus = adminFailure
    ? (confirmFailure ? "failed" : "partial")
    : (confirmFailure ? "partial" : "sent");

  try {
    await markApplicationEmail(
      applicationId,
      emailStatus,
      [confirmFailure && `confirmation: ${confirmFailure}`,
       adminFailure && `admin: ${adminFailure}`].filter(Boolean).join(" | ") || null
    );
  } catch (err) {
    console.error("[apply] could not record email status:", err);
  }

  // ── 6. Nothing recorded anywhere is not a success ──────────────────────────
  if (!applicationId && adminFailure && confirmFailure) {
    console.error("[apply] APPLICATION LOST — no database row and no email:", storeError);
    return Response.json(
      {
        error: "We could not record your application. Please email " +
               "support@qencode-benchmark.org directly and we will pick it up from there.",
      },
      { status: 503 }
    );
  }

  // The application is recorded, so a failed email is a notification problem, not a lost
  // application: it is visible in the applications table as email_status.
  console.log(
    `[apply] Application submitted — ${fields.company} <${fields.workEmail}> — ` +
    `${fields.recommendation} — row ${applicationId ?? "NONE"} — email ${emailStatus}`
  );

  return Response.json({ ok: true, recommendation: fields.recommendation });
}

export async function GET() {
  return Response.json({ error: "Method Not Allowed" }, { status: 405 });
}
