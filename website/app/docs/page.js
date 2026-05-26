import Link from "next/link";
import { ExternalLink } from "lucide-react";

export const metadata = {
  title: "Documentation",
  description:
    "QEncode documentation: quick start guide, Suite v4 benchmark specification, methodology, leaderboard rules, and technical references for reproducible VQE evaluation.",
  keywords: [
    "qencode docs",
    "quantum benchmark documentation",
    "VQE quick start",
    "leaderboard rules",
    "benchmark methodology"
  ],
  alternates: { canonical: "/docs" },
  openGraph: {
    title: "QEncode Documentation",
    description:
      "Quick start, benchmark specification, methodology, and technical references for reproducible quantum chemistry benchmarking.",
    url: "https://www.qencode-benchmark.org/docs"
  }
};

const REPO = "https://github.com/qencode-benchmark/qencode-benchmark";

const internalDocs = [
  {
    title: "Benchmark Specification",
    desc: "Suite v4 molecule catalog, qubit counts, active spaces, encoding support matrix, and ansatz definitions.",
    href: "/benchmark",
    external: false,
  },
  {
    title: "Methodology",
    desc: "Full pipeline: PySCF CASCI reference, CASSCF orbital optimization, Z2 tapering, COBYLA VQE, scoring rules, and provenance signing.",
    href: "/methodology",
    external: false,
  },
];

const repoDocs = [
  {
    title: "Quick Start Guide",
    desc: "Run your first entry in under 10 minutes. Covers environment setup, generate_entry_v4.py, and entry verification.",
    href: `${REPO}/blob/main/docs/QUICK_START.md`,
  },
  {
    title: "Benchmark Specification v4 (Markdown)",
    desc: "Machine-readable spec: geometry, active spaces, supported mappings, exclusion rules, and certification criteria.",
    href: `${REPO}/blob/main/docs/BENCHMARK_SPEC_V4.md`,
  },
  {
    title: "Leaderboard Rules",
    desc: "Eligibility, accuracy ranking, hardware cost ranking, balanced score formula, and research tab policy.",
    href: `${REPO}/blob/main/docs/LEADERBOARD_RULES_V1.md`,
  },
  {
    title: "requirements-v4.txt",
    desc: "Pinned environment: PySCF 2.5.0, PennyLane 0.45, openfermion 1.7.1. Install with pip install -r requirements-v4.txt.",
    href: `${REPO}/blob/main/requirements-v4.txt`,
  },
  {
    title: "CITATION.cff",
    desc: "How to cite QEncode in papers and grant applications.",
    href: `${REPO}/blob/main/CITATION.cff`,
  },
  {
    title: "License",
    desc: "Open-source licensing terms for using, modifying, and distributing QEncode.",
    href: `${REPO}/blob/main/LICENSE`,
  },
];

export default function DocsPage() {
  return (
    <div className="container py-16 max-w-3xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-2">Documentation</h1>
      <p className="text-muted-foreground mb-10">
        Technical references for benchmark methodology, rules, and reproducibility.
        The full suite is open source — all scripts, specs, and data are in the GitHub repository.
      </p>

      {/* Quick start */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-3">Quick start</h2>
        <div className="rounded-lg border bg-muted/30 p-5 text-sm space-y-3">
          <p className="text-muted-foreground">Run your first benchmark entry with three commands:</p>
          <pre className="bg-background border rounded-md p-4 text-xs font-mono overflow-x-auto leading-relaxed">
{`git clone https://github.com/qencode-benchmark/qencode-benchmark
pip install -r requirements-v4.txt

python scripts/generate_entry_v4.py \\
  --molecule H2 --mapping jordan_wigner \\
  --ansatz-type uccsd --out-dir releases/v4/db`}
          </pre>
          <p className="text-muted-foreground text-xs">
            Output: a signed JSON entry in <code className="font-mono bg-muted px-1 rounded">releases/v4/db/</code>{" "}
            with PySCF reference energies, VQE result, circuit metrics, and a SHA-256 provenance hash.
            Runs on any machine with Python 3.11. GPU backend available with{" "}
            <code className="font-mono bg-muted px-1 rounded">--backend lightning.gpu</code>.
          </p>
        </div>
      </section>

      {/* On-site docs */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-3">On-site documentation</h2>
        <div className="space-y-3">
          {internalDocs.map((d) => (
            <Link key={d.title} href={d.href} className="block group">
              <div className="rounded-lg border p-5 transition-shadow hover:shadow-md hover:border-primary/30">
                <h3 className="text-base font-semibold mb-1 group-hover:text-primary transition-colors">{d.title}</h3>
                <p className="text-sm text-muted-foreground">{d.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* GitHub docs */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-3">GitHub repository docs</h2>
        <div className="space-y-3">
          {repoDocs.map((d) => (
            <a key={d.title} href={d.href} target="_blank" rel="noopener noreferrer" className="block group">
              <div className="rounded-lg border p-5 transition-shadow hover:shadow-md hover:border-primary/30">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-base font-semibold mb-1 group-hover:text-primary transition-colors">{d.title}</h3>
                  <ExternalLink className="h-3.5 w-3.5 text-muted-foreground mt-1 shrink-0" />
                </div>
                <p className="text-sm text-muted-foreground">{d.desc}</p>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Certification callout */}
      <div className="rounded-lg border bg-muted/30 p-5 text-sm">
        <p className="font-medium mb-1">Need managed certification?</p>
        <p className="text-muted-foreground mb-3">
          If you need signed artifacts for a paper, grant, or hardware evaluation, apply for managed
          certification. The self-run path is always free.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/apply"
            className="inline-flex items-center rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Apply for certification
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm font-medium hover:bg-muted transition-colors"
          >
            See pricing
          </Link>
        </div>
      </div>
    </div>
  );
}
