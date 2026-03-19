export default function DocsPage() {
  const REPO_URL = "https://github.com/jlabanimation-del/qencode-benchmark-suite";
  const docs = [
    {
      title: "License",
      desc: "Open-source licensing terms for using, modifying, and distributing QEncode.",
      href: `${REPO_URL}/blob/main/LICENSE`
    },
    {
      title: "Quick Start",
      desc: "Get up and running with QEncode in minutes. Install, configure, and run your first benchmark.",
      href: `${REPO_URL}/blob/main/docs/QUICK_START.md`
    },
    {
      title: "Whitepaper",
      desc: "Read the full technical specification behind QEncode's benchmarking methodology.",
      href: `${REPO_URL}/blob/main/docs/whitepaper/QEncode%20Benchmark%20Whitepaper.pdf`
    },
    {
      title: "Benchmark Specification",
      desc: "Detailed documentation of molecules, encodings, ansatz types, and evaluation metrics.",
      href: `${REPO_URL}/blob/main/docs/Benchmark%20specification%20v1.pdf`
    },
    {
      title: "Leaderboard Rules",
      desc: "How rankings are calculated, verification criteria, and submission guidelines.",
      href: `${REPO_URL}/blob/main/docs/LEADERBOARD_RULES_V1.md`
    }
  ];

  return (
    <div className="container py-16 max-w-3xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-2">Documentation</h1>
      <p className="text-muted-foreground mb-10">Everything you need to use QEncode effectively.</p>

      <div className="space-y-4">
        {docs.map((d) => (
          <a key={d.title} href={d.href} target="_blank" rel="noopener noreferrer" className="block">
            <section className="rounded-lg border p-6 transition-shadow hover:shadow-md">
              <h3 className="text-base font-semibold mb-2">{d.title}</h3>
              <p className="text-sm text-muted-foreground">{d.desc}</p>
            </section>
          </a>
        ))}
      </div>
    </div>
  );
}

