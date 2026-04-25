import { Resend } from "resend";

const resend = new Resend(process.env.RESEND_API_KEY);

const FROM_ADDRESS = "QEncode <noreply@qencode-benchmark.org>";
const ADMIN_EMAIL = process.env.ADMIN_EMAIL || "support@qencode-benchmark.org";

/**
 * Send a payment confirmation email to the customer.
 * Called immediately after a verified order_created webhook event.
 */
export async function sendCustomerConfirmation({ customerEmail, customerName, orderId, orderNumber, productLabel, totalFormatted }) {
  const subject = `QEncode certification order #${orderNumber} confirmed`;

  const html = `
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;max-width:600px;">

        <!-- Header -->
        <tr><td style="background:#030712;padding:24px 32px;">
          <p style="margin:0;color:#ffffff;font-size:18px;font-weight:600;letter-spacing:-0.3px;">QEncode</p>
          <p style="margin:4px 0 0;color:#9ca3af;font-size:13px;">Quantum Benchmark Certification</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:32px;">
          <p style="margin:0 0 8px;font-size:22px;font-weight:600;color:#030712;">Payment confirmed</p>
          <p style="margin:0 0 24px;font-size:15px;color:#6b7280;">
            Hi ${customerName ? customerName.split(" ")[0] : "there"}, your certification order has been received and logged.
          </p>

          <!-- Order summary box -->
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;margin-bottom:24px;">
            <tr><td style="padding:20px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="font-size:13px;color:#6b7280;padding-bottom:8px;">Order</td>
                  <td align="right" style="font-size:13px;font-weight:500;color:#030712;padding-bottom:8px;">#${orderNumber} &nbsp;·&nbsp; <span style="color:#6b7280;font-weight:400;">${orderId}</span></td>
                </tr>
                <tr>
                  <td style="font-size:13px;color:#6b7280;padding-bottom:8px;">Product</td>
                  <td align="right" style="font-size:13px;font-weight:500;color:#030712;padding-bottom:8px;">${productLabel}</td>
                </tr>
                <tr>
                  <td style="font-size:13px;color:#6b7280;">Amount paid</td>
                  <td align="right" style="font-size:13px;font-weight:600;color:#030712;">${totalFormatted}</td>
                </tr>
              </table>
            </td></tr>
          </table>

          <!-- What happens next -->
          <p style="margin:0 0 12px;font-size:14px;font-weight:600;color:#030712;">What happens next</p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;">
                <p style="margin:0;font-size:13px;font-weight:500;color:#030712;">1 &nbsp; Intake confirmation</p>
                <p style="margin:4px 0 0;font-size:13px;color:#6b7280;">Our team reviews your order and sends confirmation within 1 business day.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 0;border-bottom:1px solid #f3f4f6;">
                <p style="margin:0;font-size:13px;font-weight:500;color:#030712;">2 &nbsp; Benchmark execution</p>
                <p style="margin:4px 0 0;font-size:13px;color:#6b7280;">We run your ${productLabel} on QEncode managed infrastructure. Standard turnaround: 5–10 business days.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:10px 0;">
                <p style="margin:0;font-size:13px;font-weight:500;color:#030712;">3 &nbsp; Artifacts delivered</p>
                <p style="margin:4px 0 0;font-size:13px;color:#6b7280;">Signed certification receipt, validation summary, and eligibility determination sent to this email.</p>
              </td>
            </tr>
          </table>

          <p style="margin:28px 0 0;font-size:13px;color:#6b7280;">
            Questions? Reply to this email or contact
            <a href="mailto:support@qencode-benchmark.org" style="color:#030712;font-weight:500;">support@qencode-benchmark.org</a>.
          </p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;">
          <p style="margin:0;font-size:12px;color:#9ca3af;">
            QEncode &nbsp;·&nbsp; <a href="https://www.qencode-benchmark.org" style="color:#9ca3af;">qencode-benchmark.org</a>
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>
`;

  return resend.emails.send({
    from: FROM_ADDRESS,
    to: customerEmail,
    subject,
    html,
  });
}

/**
 * Send an internal admin notification when a new order comes in.
 * This triggers the manual job queue on the Ubuntu execution machine.
 */
export async function sendAdminNotification({ customerEmail, customerName, orderId, orderNumber, productLabel, totalFormatted, rawPayload }) {
  const subject = `[QEncode] New certification order #${orderNumber} — ${productLabel}`;

  const html = `
<!DOCTYPE html>
<html lang="en">
<body style="font-family:monospace;padding:24px;background:#fff;">
  <h2 style="margin:0 0 16px;font-size:16px;">New certification order received</h2>
  <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:13px;">
    <tr><td style="padding:4px 12px 4px 0;color:#666;">Order #</td><td style="padding:4px 0;font-weight:600;">${orderNumber}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666;">Order ID</td><td style="padding:4px 0;">${orderId}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666;">Customer</td><td style="padding:4px 0;">${customerName || "(not provided)"}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666;">Email</td><td style="padding:4px 0;"><a href="mailto:${customerEmail}">${customerEmail}</a></td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666;">Product</td><td style="padding:4px 0;font-weight:600;">${productLabel}</td></tr>
    <tr><td style="padding:4px 12px 4px 0;color:#666;">Amount</td><td style="padding:4px 0;">${totalFormatted}</td></tr>
  </table>

  <h3 style="margin:24px 0 8px;font-size:14px;">Action required on Ubuntu</h3>
  <pre style="background:#f4f4f4;padding:12px;border-radius:4px;font-size:12px;overflow-x:auto;">cd ~/work/qencode-db
conda activate qencode

# Then run the appropriate job for this order:
# Full Suite v2 → python scripts/run_certified_job.py --suite v2 --order ${orderNumber} --email ${customerEmail}
# Single Molecule → python scripts/run_certified_job.py --molecule &lt;name&gt; --order ${orderNumber} --email ${customerEmail}
</pre>

  <details style="margin-top:16px;">
    <summary style="cursor:pointer;font-size:12px;color:#666;">Full webhook payload (expand)</summary>
    <pre style="background:#f4f4f4;padding:12px;border-radius:4px;font-size:11px;overflow-x:auto;margin-top:8px;">${rawPayload}</pre>
  </details>
</body>
</html>
`;

  return resend.emails.send({
    from: FROM_ADDRESS,
    to: ADMIN_EMAIL,
    subject,
    html,
  });
}

// ─── Apply form emails ────────────────────────────────────────────────────────

/**
 * Confirm to the applicant that their form was received.
 */
export async function sendApplyConfirmation({ contactName, workEmail, company, recommendation }) {
  const subject = "QEncode access application received";

  const html = `
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:40px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;max-width:600px;">
        <tr><td style="background:#030712;padding:24px 32px;">
          <p style="margin:0;color:#ffffff;font-size:18px;font-weight:600;letter-spacing:-0.3px;">QEncode</p>
          <p style="margin:4px 0 0;color:#9ca3af;font-size:13px;">Quantum Benchmark Certification</p>
        </td></tr>
        <tr><td style="padding:32px;">
          <p style="margin:0 0 8px;font-size:22px;font-weight:600;color:#030712;">Application received</p>
          <p style="margin:0 0 24px;font-size:15px;color:#6b7280;">
            Hi ${contactName ? contactName.split(" ")[0] : "there"}, we've received your access application for <strong style="color:#030712;">${company}</strong>.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;margin-bottom:24px;">
            <tr><td style="padding:16px 20px;">
              <p style="margin:0 0 4px;font-size:13px;color:#6b7280;">Auto-recommended plan</p>
              <p style="margin:0;font-size:16px;font-weight:600;color:#030712;">${recommendation}</p>
            </td></tr>
          </table>
          <p style="margin:0 0 12px;font-size:14px;font-weight:600;color:#030712;">What happens next</p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td style="padding:10px 0;border-bottom:1px solid #f3f4f6;">
              <p style="margin:0;font-size:13px;font-weight:500;color:#030712;">1 &nbsp; Review</p>
              <p style="margin:4px 0 0;font-size:13px;color:#6b7280;">Our team reviews your application within 1–2 business days.</p>
            </td></tr>
            <tr><td style="padding:10px 0;">
              <p style="margin:0;font-size:13px;font-weight:500;color:#030712;">2 &nbsp; Response</p>
              <p style="margin:4px 0 0;font-size:13px;color:#6b7280;">We'll reply with access scope, recommended plan, and next steps tailored to your workload.</p>
            </td></tr>
          </table>
          <p style="margin:28px 0 0;font-size:13px;color:#6b7280;">
            Questions? Reply to this email or contact
            <a href="mailto:support@qencode-benchmark.org" style="color:#030712;font-weight:500;">support@qencode-benchmark.org</a>.
          </p>
        </td></tr>
        <tr><td style="background:#f9fafb;padding:16px 32px;border-top:1px solid #e5e7eb;">
          <p style="margin:0;font-size:12px;color:#9ca3af;">
            QEncode &nbsp;·&nbsp; <a href="https://www.qencode-benchmark.org" style="color:#9ca3af;">qencode-benchmark.org</a>
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;

  return resend.emails.send({
    from: FROM_ADDRESS,
    to: workEmail,
    subject,
    html,
  });
}

/**
 * Notify admin of a new access application.
 */
export async function sendApplyAdminNotification(fields) {
  const { company, contactName, workEmail, role, moleculeScope, timeline,
          monthlyRuns, needsCertification, needsPrivateBenchmark, notes, recommendation } = fields;

  const subject = `[QEncode] New access application — ${company}`;

  const row = (label, value) =>
    `<tr><td style="padding:4px 12px 4px 0;color:#666;font-size:13px;white-space:nowrap;">${label}</td><td style="padding:4px 0;font-size:13px;">${value || "—"}</td></tr>`;

  const html = `
<!DOCTYPE html>
<html lang="en">
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:24px;background:#fff;">
  <h2 style="margin:0 0 16px;font-size:16px;">New access application</h2>
  <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    ${row("Company/Lab", `<strong>${company}</strong>`)}
    ${row("Contact", contactName)}
    ${row("Email", `<a href="mailto:${workEmail}">${workEmail}</a>`)}
    ${row("Role", role)}
    ${row("Molecule Scope", moleculeScope)}
    ${row("Timeline", timeline)}
    ${row("Monthly Runs", monthlyRuns)}
    ${row("Needs Certification", needsCertification)}
    ${row("Needs Private Benchmark", needsPrivateBenchmark)}
    ${row("Recommended Plan", `<strong>${recommendation}</strong>`)}
    ${row("Notes", notes)}
  </table>
  <p style="margin-top:24px;font-size:13px;color:#666;">
    Reply directly to <a href="mailto:${workEmail}">${workEmail}</a> to respond.
  </p>
</body>
</html>`;

  return resend.emails.send({
    from: FROM_ADDRESS,
    to: ADMIN_EMAIL,
    replyTo: workEmail,
    subject,
    html,
  });
}
