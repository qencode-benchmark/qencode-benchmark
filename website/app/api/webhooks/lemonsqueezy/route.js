import { createHmac, timingSafeEqual } from "crypto";
import { sendCustomerConfirmation, sendAdminNotification } from "@/lib/email";
import { ensureSchema, insertOrder } from "@/lib/db";

/**
 * POST /api/webhooks/lemonsqueezy
 *
 * Receives order events from Lemon Squeezy and:
 *  1. Verifies the HMAC-SHA256 signature
 *  2. Fires customer confirmation email
 *  3. Fires admin notification email (triggers Ubuntu execution queue)
 *
 * Required env vars:
 *  LEMONSQUEEZY_WEBHOOK_SECRET — signing secret from LS dashboard
 *  RESEND_API_KEY              — Resend API key for transactional email
 *  ADMIN_EMAIL                 — (optional) override admin notification target
 *
 * Lemon Squeezy docs:
 *  https://docs.lemonsqueezy.com/help/webhooks
 */

// Map Lemon Squeezy product names / price thresholds to human-readable labels.
// We use price (in cents) as the primary key because product names can change.
function resolveProduct(attrs) {
  const total = attrs.total ?? 0;
  const productName = attrs.first_order_item?.product_name ?? "";

  if (total >= 390000 || /full suite/i.test(productName)) {
    return { label: "Full Suite v2 Certification", type: "full_suite" };
  }
  if (total >= 140000 || /single.?molecule/i.test(productName)) {
    return { label: "Single-Molecule Certification", type: "single_molecule" };
  }
  return { label: productName || `Order ($${(total / 100).toFixed(2)})`, type: "unknown" };
}

/** Verify the X-Signature header using HMAC-SHA256 */
async function verifySignature(rawBody, signatureHeader) {
  const secret = process.env.LEMONSQUEEZY_WEBHOOK_SECRET;
  if (!secret) {
    console.error("[lemonsqueezy] LEMONSQUEEZY_WEBHOOK_SECRET is not set");
    return false;
  }
  if (!signatureHeader) return false;

  const hmac = createHmac("sha256", secret);
  hmac.update(rawBody);
  const digest = hmac.digest("hex");

  try {
    // timingSafeEqual prevents timing attacks
    return timingSafeEqual(
      Buffer.from(signatureHeader, "hex"),
      Buffer.from(digest, "hex")
    );
  } catch {
    return false;
  }
}

export async function POST(request) {
  // ── 1. Read raw body (must happen before any .json() call) ──────────────
  let rawBody;
  try {
    rawBody = await request.text();
  } catch (err) {
    console.error("[lemonsqueezy] Failed to read request body:", err);
    return new Response("Bad Request", { status: 400 });
  }

  // ── 2. Verify signature ──────────────────────────────────────────────────
  const signature = request.headers.get("x-signature");
  const valid = await verifySignature(rawBody, signature);

  if (!valid) {
    console.warn("[lemonsqueezy] Invalid signature — request rejected");
    return new Response("Unauthorized", { status: 401 });
  }

  // ── 3. Parse payload ─────────────────────────────────────────────────────
  let payload;
  try {
    payload = JSON.parse(rawBody);
  } catch (err) {
    console.error("[lemonsqueezy] Failed to parse JSON:", err);
    return new Response("Bad Request", { status: 400 });
  }

  const eventName = payload?.meta?.event_name;
  console.log(`[lemonsqueezy] Event received: ${eventName}`);

  // ── 4. Handle order_created ──────────────────────────────────────────────
  if (eventName === "order_created") {
    const attrs = payload?.data?.attributes ?? {};
    const orderId = payload?.data?.id ?? "unknown";

    // Only process paid orders (ignore pending/refunded/etc.)
    if (attrs.status !== "paid") {
      console.log(`[lemonsqueezy] Order ${orderId} status is "${attrs.status}" — skipping email`);
      return new Response("OK", { status: 200 });
    }

    const customerEmail = attrs.user_email;
    const customerName = attrs.user_name;
    const orderNumber = attrs.order_number;
    const totalFormatted = attrs.total_formatted ?? `$${(attrs.total / 100).toFixed(2)}`;
    const { label: productLabel, type: productType } = resolveProduct(attrs);

    if (!customerEmail) {
      console.error("[lemonsqueezy] Order has no customer email — cannot send confirmation");
      return new Response("OK", { status: 200 }); // Still 200 so LS doesn't retry
    }

    console.log(`[lemonsqueezy] Processing paid order #${orderNumber} for ${customerEmail} — ${productLabel}`);

    // ── 5. Log order to DB + send emails in parallel ─────────────────────────
    const [dbResult, ...emailResults] = await Promise.allSettled([
      (async () => {
        await ensureSchema();
        await insertOrder({
          lsOrderId:      String(orderId),
          lsOrderNumber:  orderNumber,
          customerEmail,
          customerName,
          productLabel,
          productType,
          totalFormatted,
        });
        console.log(`[lemonsqueezy] Order #${orderNumber} saved to DB — status: pending`);
      })(),
      sendCustomerConfirmation({
        customerEmail,
        customerName,
        orderId,
        orderNumber,
        productLabel,
        totalFormatted,
      }),
      sendAdminNotification({
        customerEmail,
        customerName,
        orderId,
        orderNumber,
        productLabel,
        totalFormatted,
        rawPayload: JSON.stringify(payload, null, 2),
      }),
    ]);

    if (dbResult.status === "rejected") {
      console.error("[lemonsqueezy] Failed to save order to DB:", dbResult.reason);
    }

    emailResults.forEach((result, i) => {
      const label = i === 0 ? "customer confirmation" : "admin notification";  // emailResults[0] is confirm, [1] is admin
      if (result.status === "rejected") {
        console.error(`[lemonsqueezy] Failed to send ${label}:`, result.reason);
      } else if (result.value?.error) {
        console.error(`[lemonsqueezy] Resend error for ${label}:`, result.value.error);
      } else {
        console.log(`[lemonsqueezy] Sent ${label} — id: ${result.value?.data?.id}`);
      }
    });
  }

  // ── 6. Always return 200 for handled events ───────────────────────────────
  // Lemon Squeezy retries on non-2xx, so we return 200 even if email failed.
  return new Response("OK", { status: 200 });
}

// Lemon Squeezy only sends POST — reject other methods cleanly
export async function GET() {
  return new Response("Method Not Allowed", { status: 405 });
}
