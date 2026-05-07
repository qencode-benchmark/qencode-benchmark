import Link from "next/link";

export const metadata = {
  title: "Documentation",
  description:
    "Access QEncode benchmark documentation, quick start guides, benchmark rules, methodology, and technical references for reproducible quantum algorithm evaluation.",
  keywords: [
    "qencode docs",
    "quantum benchmark documentation",
    "leaderboard rules",
    "benchmark methodology"
  ],
  alternates: {
    canonical: "/docs"
  },
  openGraph: {
    title: "QEncode Documentation",
    description:
      "Technical references for benchmark methodology, leaderboard rules, and reproducible quantum benchmarking workflows.",
    url: "/docs"
  }
};

export default function DocsPage() {
  const REPO_URL = "https://github.com/qencode-benchmark/qencode-benchmark";
  const docs = [
    {
      title: "License",
      desc: "Open-source licensing terms for using, modifying, and distributing QEncode.",
      href: `${REPO_URL}/blob/main/LICENSE`
    },
    {
      title: "Quick Start",
      desc: "Technical quick-start for local validation and reproducibility checks.",
      href: `${REPO_URL}/blob/main/docs/QUICK_START.md`
    },
    {
      title: "Whitepaper",
      desc: "Read the full technical specification behind QEncode's benchmarking methodology.",
      href: `${REPO_URL}/tree/main/docs/whitepaper`
    },
    {
      title: "Benchmark Specification",
      desc: "Fixed suite definitions for molecules, encodings, ansatz types, and evaluation metrics.",
      href: `${REPO_URL}/blob/main/docs/BENCHMARK_SPEC_V2.md`
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
      <p className="text-muted-foreground mb-6">Technical references for benchmark methodology, rules, and reproducibility.</p>
      <div className="rounded-lg border p-4 bg-muted/30 text-sm text-muted-foreground mb-10">
        Looking for managed execution access or commercial onboarding? Start at{" "}
        <Link className="text-primary underline underline-offset-2" href="/apply">Apply for Access</Link>{" "}
        and review plan options at{" "}
        <Link className="text-primary underline underline-offset-2" href="/pricing">Pricing</Link>.
      </div>

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

