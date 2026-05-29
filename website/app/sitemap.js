const BASE_URL = "https://www.qencode-benchmark.org";

const blogPosts = [
  { slug: "adapt-vqe-certifies-benzene",            date: "2026-05-29" },
  { slug: "benzene-first-aromatic-molecule",         date: "2026-05-27" },
  { slug: "certifying-n2-triple-bond",              date: "2026-05-21" },
  { slug: "h2o-first-8-qubit-benchmark",            date: "2026-05-07" },
  { slug: "chemical-accuracy-vs-certification",      date: "2026-05-07" },
  { slug: "jordan-wigner-vs-parity-vs-bravyi-kitaev", date: "2026-04-25" },
  { slug: "uccsd-vs-hardware-efficient-ansatz",      date: "2026-04-25" },
  { slug: "vqe-benchmarking-reproducibility",        date: "2026-04-18" },
];

export default function sitemap() {
  const now = new Date();

  const staticRoutes = [
    { route: "",             priority: 1.0, freq: "weekly"  },
    { route: "/leaderboard", priority: 0.9, freq: "daily"   },
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
  ];
}