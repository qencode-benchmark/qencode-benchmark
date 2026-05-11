import { ensureSchema, getEntries, getMetadata } from "@/lib/db";

/**
 * GET /api/leaderboard
 *
 * Public JSON API for leaderboard data. No auth required.
 *
 * Query params:
 *   category  — "accuracy" | "cost" | "balanced" | "all"  (default: "all")
 *   molecule  — filter by molecule name, e.g. "H2", "LiH"
 *   ansatz    — filter by ansatz, e.g. "uccsd", "hardware_efficient"
 *   mapping   — filter by encoding, e.g. "parity", "jordan_wigner", "bravyi_kitaev"
 *
 * Response:
 * {
 *   "version": "v2",
 *   "generated": "2026-04-26T...",
 *   "categories": {
 *     "accuracy": [...],
 *     "cost":     [...],
 *     "balanced": [...]
 *   },
 *   "metadata": { ... }
 * }
 */

const VALID_CATEGORIES = ["accuracy", "cost", "balanced", "research"];

function applyFilters(entries, { molecule, ansatz, mapping }) {
  return entries.filter((e) => {
    if (molecule && e.molecule?.toLowerCase() !== molecule.toLowerCase()) return false;
    if (ansatz  && e.ansatz?.toLowerCase()  !== ansatz.toLowerCase())   return false;
    if (mapping && e.mapping?.toLowerCase() !== mapping.toLowerCase())  return false;
    return true;
  });
}

export async function GET(request) {
  const { searchParams } = new URL(request.url);
  const categoryParam = searchParams.get("category") ?? "all";
  const molecule      = searchParams.get("molecule") ?? "";
  const ansatz        = searchParams.get("ansatz")   ?? "";
  const mapping       = searchParams.get("mapping")  ?? "";

  // Validate category param
  if (categoryParam !== "all" && !VALID_CATEGORIES.includes(categoryParam)) {
    return Response.json(
      { error: `Invalid category. Use: ${VALID_CATEGORIES.join(", ")}, or "all"` },
      { status: 400 }
    );
  }

  try {
    await ensureSchema();

    const categories = categoryParam === "all" ? VALID_CATEGORIES : [categoryParam];

    const [results, metadata] = await Promise.all([
      Promise.all(
        categories.map(async (cat) => {
          const entries = await getEntries(cat);
          const filtered = applyFilters(entries, { molecule, ansatz, mapping });
          return [cat, filtered];
        })
      ),
      getMetadata(),
    ]);

    const categoriesObj = Object.fromEntries(results);

    return Response.json(
      {
        version:    metadata.suite_version ?? "v3",
        rules:      metadata.leaderboard_rules ?? "v1",
        generated:  new Date().toISOString(),
        filters:    { category: categoryParam, molecule: molecule || null, ansatz: ansatz || null, mapping: mapping || null },
        categories: categoriesObj,
        metadata,
      },
      {
        headers: {
          // Allow anyone to query this (CORS open)
          "Access-Control-Allow-Origin": "*",
          // Cache for 60 seconds on CDN, but always revalidate
          "Cache-Control": "public, max-age=60, stale-while-revalidate=300",
        },
      }
    );
  } catch (err) {
    console.error("[api/leaderboard] GET failed:", err);
    return Response.json({ error: "Failed to fetch leaderboard data" }, { status: 500 });
  }
}

// Handle CORS preflight
export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin":  "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    },
  });
}
