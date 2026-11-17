import { loadLeaderboardData } from "@/lib/data";

const BASE_URL = "https://www.qencode-benchmark.org";

// Entry URLs come from live sources, so render on request.
export const dynamic = "force-dynamic";

const GITHUB_DB_LISTING =
  "https://api.github.com/repos/qencode-benchmark/qencode-benchmark/contents/releases/v4/db?ref=master";

/** Entry IDs linked from the leaderboard (certified and research tier). */
async function leaderboardIds() {
  try {
    const { acc = [], cost = [], balanced = [], research = [] } = await loadLeaderboardData();
    return [...acc, ...cost, ...balanced, ...research].map((r) => r.entryId).filter(Boolean);
  } catch (err) {
    console.error("[sitemap] could not load leaderboard entries:", err?.message ?? err);
    return [];
  }
}

/**
 * Entry IDs published in the public repository. Includes research-tier runs the
 * leaderboard does not link (e.g. the N₂ four-layer COBYLA result). Cached for an
 * hour so the unauthenticated GitHub API limit is never a concern.
 */
async function repositoryIds() {
  try {
    const res = await fetch(GITHUB_DB_LISTING, {
      headers: { Accept: "application/vnd.github+json" },
      next: { revalidate: 3600 },
    });
    if (!res.ok) throw new Error(`GitHub listing HTTP ${res.status}`);
    const files = await res.json();
    return files
      .map((f) => f.name)
      .filter((n) => typeof n === "string" && n.endsWith(".json"))
      .map((n) => n.slice(0, -".json".length));
  } catch (err) {
    console.error("[sitemap] could not list repository entries:", err?.message ?? err);
    return [];
  }
}

/** Every published entry page. Never fails the sitemap if a source is unreachable. */
async function entryUrls() {
  const [db, repo] = await Promise.all([leaderboardIds(), repositoryIds()]);
  const ids = new Set([...db, ...repo]);
  return [...ids].sort().map((id) => ({
    url: `${BASE_URL}/entry/${id}`,
    changeFrequency: "monthly",
    priority: 0.6,
  }));
}

const blogPosts = [
  { slug: "verifying-the-whole-database",         date: "2026-09-03" },
  { slug: "shot-allocation-neyman-trap",            date: "2026-08-27" },
  { slug: "vqe-reproducibility-scorecard",          date: "2026-07-28" },
  { slug: "vqe-reproducibility-threading-bug",      date: "2026-07-16" },
  { slug: "adapt-vqe-certifies-benzene",            date: "2026-05-29" },
  { slug: "benzene-first-aromatic-molecule",         date: "2026-05-27" },
  { slug: "certifying-n2-triple-bond",              date: "2026-05-21" },
  { slug: "h2o-first-8-qubit-benchmark",            date: "2026-05-07" },
  { slug: "chemical-accuracy-vs-certification",      date: "2026-05-07" },
  { slug: "jordan-wigner-vs-parity-vs-bravyi-kitaev", date: "2026-04-25" },
  { slug: "uccsd-vs-hardware-efficient-ansatz",      date: "2026-04-25" },
  { slug: "vqe-benchmarking-reproducibility",        date: "2026-04-18" },
];

export default async function sitemap() {
  const now = new Date();

  const staticRoutes = [
    { route: "",             priority: 1.0, freq: "weekly"  },
    { route: "/leaderboard", priority: 0.9, freq: "daily"   },
    { route: "/score",       priority: 0.9, freq: "monthly" },
    { route: "/leaderboard/guide", priority: 0.7, freq: "monthly" },
    { route: "/benchmark",   priority: 0.8, freq: "monthly" },
    { route: "/methodology", priority: 0.8, freq: "monthly" },
    { route: "/blog",        priority: 0.8, freq: "weekly"  },
    { route: "/about",       priority: 0.7, freq: "monthly" },
    { route: "/docs",        priority: 0.7, freq: "monthly" },
    { route: "/apply",       priority: 0.7, freq: "monthly" },
    { route: "/pricing",     priority: 0.6, freq: "monthly" },
    { route: "/certify",     priority: 0.5, freq: "monthly" },
  ];

  const blogEntries = blogPosts.map(({ slug, date }) => ({
    url: `${BASE_URL}/blog/${slug}`,
    lastModified: new Date(date),
    changeFrequency: "monthly",
    priority: 0.8,
  }));

  return [
    ...staticRoutes.map(({ route, priority, freq }) => ({
      url: `${BASE_URL}${route}`,
      lastModified: now,
      changeFrequency: freq,
      priority,
    })),
    ...blogEntries,
    ...(await entryUrls()),
  ];
}