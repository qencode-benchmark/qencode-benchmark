import Link from "next/link";
import { CheckCircle, GitFork, ExternalLink } from "lucide-react";

export const metadata = {
  title: "About QEncode",
  description:
    "QEncode is an open-source benchmark standard for reproducible VQE quantum chemistry evaluation. 39 certified entries, cc-pVDZ basis, N₂ certified with CASSCF — aligned with DARPA QB-GSEE targets.",
  keywords: [
    "about qencode",
    "quantum benchmark standard",
    "quantum algorithm certification",
    "reproducible quantum evaluation",
    "DARPA QB-GSEE"
  ],
  alternates: { canonical: "/about" },
  openGraph: {
    title: "About QEncode — Quantum Benchmark Standard",
    description:
      "QEncode provides the open benchmark standard and certification infrastructure for reproducible quantum algorithm evaluation. Free to run. Certified results for publications.",
    url: "https://www.qencode-benchmark.org/about"
  }
};

const achievements = [
  {
    label: "39 certified entries",
    detail: "Across 14 molecules at cc-pVDZ basis — H₂, HF, LiH, BeH₂, H₂O, NH₃, H₂CO, C₄H₆, H₄, N₂, H₆, benzene, H₈, and H₁₀."
  },
  {
    label: "N₂ certified — 2.0 mHa gap",
    detail: "12 qubits, CASSCF orbital optimization, 404 UCCSD parameters. DARPA QB-GSEE benchmark candidate."
  },
  {
    label: "Benzene certified — first aromatic",
    detail: "[6e,6o] π active space, D6h symmetry, CASSCF orbitals, certified via ADAPT-VQE at a 6.991 mHa best gap — direct relevance to pharmaceutical chemistry."
  },
  {
    label: "H₁₀ certified — largest system in the suite",
    detail: "[10e,10o] active space, 20 JW qubits tapered to 18, CASSCF orbitals, certified via ADAPT-VQE at a 9.977 mHa best gap. DARPA QB-GSEE aligned."
  },
  {
    label: "Ed25519-signed artifacts",
    detail: "Every certified entry carries a cryptographic signature and SHA-256 provenance hash."
  },
  {
    label: "Fully open data",
    detail: "All entries, reference energies, and run configs published in the public GitHub repository."
  },
];

const principles = [
  {
    title: "Results are never fabricated",
    desc: "Every number comes from the real pipeline: PySCF computes the reference, PennyLane runs the circuit, gap = |E_VQE − E_CASCI| computed from real outputs. If a molecule fails to converge, the result is recorded as-is — never discarded or adjusted."
  },
  {
    title: "Methodology is always public",
    desc: "The full benchmark specification, execution scripts, and requirements files are open source. Anyone can reproduce any entry with a single command. The certification layer adds signatures and managed execution — it does not change the methodology."
  },
  {
    title: "Free to run, certified when needed",
    desc: "The self-run path is free and always will be. Managed certification — with signed artifacts, provenance receipts, and audit-ready reports — is available for teams that need verified results for publications, grant applications, or hardware evaluations."
  },
  {
    title: "The leaderboard records what actually happened",
    desc: "Validated entries that don't pass certification (gap ≥ 0.01 Ha) appear in the Research tab, not the trash. The N₂ HEA result — 0.121 Ha gap across 30 restarts — is as informative as the 2.0 mHa UCCSD result. Both are in the database."
  },
];

export default function AboutPage() {
  return (
    <div className="container py-16 max-w-3xl">

      <h1 className="text-3xl sm:text-4xl font-bold mb-4">About QEncode</h1>

      <p className="text-lg text-muted-foreground leading-relaxed mb-4">
        QEncode is an open-source benchmark standard and certification platform for reproducible
        VQE quantum chemistry evaluation. Our goal is to be the accepted standard for quantum
        algorithm performance — the same role that MLPerf plays in classical machine learning.
      </p>

      <p className="text-muted-foreground leading-relaxed mb-10">
        Quantum algorithm results published today are almost impossible to compare across papers and
        platforms. Different molecule choices, basis sets, active space definitions, encodings, ansatz
        settings, optimizer parameters, and runtime environments mean that two papers claiming to
        solve the same problem are often solving completely different ones. QEncode fixes this with
        a fixed benchmark suite, a single reference standard (CASCI at cc-pVDZ), and signed
        certification artifacts that make every result independently verifiable.
      </p>

      {/* What we've built */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">What we&apos;ve built</h2>
        <div className="space-y-3">
          {achievements.map((a) => (
            <div key={a.label} className="flex items-start gap-3 rounded-lg border p-4">
              <CheckCircle className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
              <div>
                <p className="font-medium text-sm">{a.label}</p>
                <p className="text-sm text-muted-foreground mt-0.5">{a.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Why it matters */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-2">Why this matters</h2>
        <p className="text-muted-foreground text-sm mb-5">
          DARPA&apos;s Quantum Benchmarking program (QB-GSEE) explicitly targets ground-state energy
          estimation for molecules where classical methods are insufficient. QEncode&apos;s certified N₂
          result at cc-pVDZ with a [6e,6o] active space is directly comparable to the QB-GSEE target
          specification — with a provenance hash and Ed25519 signature that makes the claim verifiable.
        </p>
        <p className="text-muted-foreground text-sm">
          As quantum hardware moves toward fault tolerance, the field needs a trusted benchmark that
          hardware teams, algorithm researchers, and program officers can all point to. QEncode is
          building that infrastructure now, starting with near-term VQE on classical simulators and
          extending to real hardware certification in v4.4.
        </p>
      </section>

      {/* Principles */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Core principles</h2>
        <div className="space-y-4">
          {principles.map((p) => (
            <div key={p.title} className="rounded-lg border p-5">
              <h3 className="font-semibold text-sm mb-1">{p.title}</h3>
              <p className="text-sm text-muted-foreground">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Vision */}
      <section className="rounded-lg border bg-muted/30 p-6 mb-8">
        <h2 className="font-semibold mb-2">Vision</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Independent, signed proof that your quantum algorithm or hardware outperforms classical
          methods on real chemistry benchmarks — accessible to every researcher, trusted by every reviewer.
        </p>
      </section>

      {/* CTA */}
      <div className="flex flex-wrap gap-3">
        <a
          href="https://github.com/qencode-benchmark/qencode-benchmark"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <GitFork className="h-4 w-4" /> GitHub repository
        </a>
        <Link
          href="/leaderboard"
          className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
        >
          View leaderboard
        </Link>
        <Link
          href="/blog"
          className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
        >
          Read the blog
        </Link>
      </div>

      <p className="mt-8 text-sm text-muted-foreground">
        Questions?{" "}
        <a href="mailto:support@qencode-benchmark.org" className="text-primary hover:underline">
          support@qencode-benchmark.org
        </a>
      </p>
    </div>
  );
}
