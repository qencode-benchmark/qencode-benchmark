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

// All repository links use blob/HEAD, which resolves to whatever the default branch is.
// They previously used blob/main — a branch 249 commits behind master, so those links
// either 404ed or silently served content from April.
const internalDocs = [
  {
    title: "Score your own VQE result",
    desc: "Compare an energy you already have against the exact active-space ground state, in one function call. Reports the gap, the certification margin, and whether your optimiser and ansatz make that margin fragile.",
    href: "/score",
    external: false,
  },
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
  {
    title: "Reading the leaderboard",
    desc: "What the gap is measured against, the two thresholds, the certification margin, the optimiser chip, and what the CCSD(T) badge does and does not claim.",
    href: "/leaderboard/guide",
    external: false,
  },
];

const repoDocs = [
  {
    title: "Scoring notebook",
    desc: "Executable walkthrough of qencode.score: edit one cell with your energy and run it top to bottom. Outputs are committed, so it reads on GitHub without being run.",
    href: `${REPO}/blob/HEAD/notebooks/score_your_vqe_result.ipynb`,
  },
  {
    title: "Quick Start Guide",
    desc: "Run your first entry in under 10 minutes. Covers environment setup, entry generation, and verification.",
    href: `${REPO}/blob/HEAD/QUICKSTART.md`,
  },
  {
    title: "Trust Policy",
    desc: "The single definition of certified: gap below 10 mHa against the active-space CASCI reference. What certification attests, what it does not, and the markers that are reported but are not certification.",
    href: `${REPO}/blob/HEAD/docs/TRUST_POLICY.md`,
  },
  {
    title: "Leaderboard Rules",
    desc: "Eligibility, accuracy ranking, hardware cost ranking, balanced score formula, research tier policy, and the dated amendments on reproducibility and certification margin.",
    href: `${REPO}/blob/HEAD/docs/LEADERBOARD_RULES_V2.md`,
  },
  {
    title: "Verification sweep",
    desc: "The first end-to-end re-run of all 54 published entries, the three verifier bugs it found, and what reproducibility means across machines for gradient-free optimisers.",
    href: `${REPO}/blob/HEAD/docs/VERIFICATION_SWEEP.md`,
  },
  {
    title: "requirements-v4.txt",
    desc: "Pinned environment: PySCF 2.6.2, PennyLane 0.45.0, openfermion 1.6.1, NumPy 2.2.6, SciPy 1.13.1. Exact pins, not lower bounds — a VQE result is only reproducible if the stack is.",
    href: `${REPO}/blob/HEAD/requirements-v4.txt`,
  },
  {
    title: "CITATION.cff",
    desc: "How to cite QEncode in papers and grant applications.",
    href: `${REPO}/blob/HEAD/CITATION.cff`,
  },
  {
    title: "License",
    desc: "Open-source licensing terms for using, modifying, and distributing QEncode.",
    href: `${REPO}/blob/HEAD/LICENSE`,
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

      {/* Score an existing result */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-3">Already have a VQE energy?</h2>
        <div className="rounded-lg border bg-muted/30 p-5 text-sm space-y-3">
          <p className="text-muted-foreground">
            Score it against the exact active-space ground state without running the pipeline.
            No clone, and no chemistry stack — the reference energies ship inside the package.
          </p>
          <pre className="bg-background border rounded-md p-4 text-xs font-mono overflow-x-auto leading-relaxed">
{`pip install qencode-benchmark

python -c "
import qencode
s = qencode.score(-7.9835, molecule='LiH', active_space=(4, 4),
                  optimizer='COBYLA', ansatz='hea')
print(s.report())"`}
          </pre>
          <p className="text-muted-foreground text-xs">
            Reports the gap to exact diagonalisation, which of the two thresholds it clears, the
            certification margin, whether your optimiser and ansatz make that margin fragile across
            machines, and the rank among published entries.{" "}
            <Link href="/score" className="text-primary hover:underline font-medium">Full guide →</Link>
          </p>
        </div>
      </section>

      {/* Quick start */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-3">Generate a benchmark entry</h2>
        <div className="rounded-lg border bg-muted/30 p-5 text-sm space-y-3">
          <p className="text-muted-foreground">
            The full pipeline: computes the CASCI reference, runs the VQE, and writes a hashed entry.
            Needs the chemistry stack, which the package pulls in.
          </p>
          <pre className="bg-background border rounded-md p-4 text-xs font-mono overflow-x-auto leading-relaxed">
{`pip install qencode-benchmark

qencode run --molecule H2 --mapping jordan_wigner \\
  --ansatz-type uccsd --out-dir out`}
          </pre>
          <p className="text-muted-foreground text-xs">
            Output: a JSON entry with PySCF reference energies, the VQE result, circuit metrics and a
            SHA-256 provenance hash. About ten seconds for H₂. Clone the repository instead if you
            want the entry database and the producing commit recorded inside each entry. GPU backend
            available with <code className="font-mono bg-muted px-1 rounded">--backend lightning.gpu</code>.
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
