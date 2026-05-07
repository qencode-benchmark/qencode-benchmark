import { getCertificationByToken } from "@/lib/db";

/**
 * GET /api/badge/[token]
 *
 * Returns an SVG badge for a verified certification.
 * Use in GitHub README:
 *   ![QEncode Certified](https://www.qencode-benchmark.org/api/badge/YOUR_TOKEN)
 *
 * Returns:
 *   - 200 + SVG  if token is valid and order is completed
 *   - 404 + SVG  if token not found (shows "not found" badge)
 */

function makeSvg({ label, message, color }) {
  const labelWidth  = label.length  * 6.5 + 16;
  const messageWidth = message.length * 6.5 + 16;
  const totalWidth  = labelWidth + messageWidth;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${totalWidth}" height="20" role="img" aria-label="${label}: ${message}">
  <title>${label}: ${message}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="${totalWidth}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="${labelWidth}" height="20" fill="#0f172a"/>
    <rect x="${labelWidth}" width="${messageWidth}" height="20" fill="${color}"/>
    <rect width="${totalWidth}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="${labelWidth / 2}" y="15" fill="#010101" fill-opacity=".3" aria-hidden="true">${label}</text>
    <text x="${labelWidth / 2}" y="14">${label}</text>
    <text x="${labelWidth + messageWidth / 2}" y="15" fill="#010101" fill-opacity=".3" aria-hidden="true">${message}</text>
    <text x="${labelWidth + messageWidth / 2}" y="14">${message}</text>
  </g>
</svg>`;
}

export async function GET(request, { params }) {
  const { token } = await params;

  const headers = {
    "Content-Type":  "image/svg+xml",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Access-Control-Allow-Origin": "*",
  };

  // Invalid UUID format → 404 badge
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!UUID_RE.test(token)) {
    return new Response(
      makeSvg({ label: "QEncode", message: "not found", color: "#e05d44" }),
      { status: 404, headers }
    );
  }

  try {
    const cert = await getCertificationByToken(token);

    if (!cert) {
      return new Response(
        makeSvg({ label: "QEncode", message: "not found", color: "#e05d44" }),
        { status: 404, headers }
      );
    }

    // Shorten product label for badge display
    const message = cert.product_type === "full_suite"
      ? "Suite v2 certified ✓"
      : "certified ✓";

    return new Response(
      makeSvg({ label: "QEncode", message, color: "#22c55e" }),
      { status: 200, headers }
    );
  } catch (err) {
    console.error("[badge] GET failed:", err);
    return new Response(
      makeSvg({ label: "QEncode", message: "error", color: "#9f9f9f" }),
      { status: 500, headers }
    );
  }
}
