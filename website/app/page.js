import Link from "next/link";
import Image from "next/image";
import { ArrowRight, BarChart3, Shield, Trophy, Database, CheckCircle, ExternalLink, GitFork } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "Quantum Algorithm Benchmarking Platform",
  description:
    "QEncode is an open-source benchmark standard for reproducible VQE quantum chemistry evaluation. 47 certified entries across 16 molecules. Free to run. Certification optional.",
  keywords: [
    "quantum algorithm benchmarking platform",
    "VQE leaderboard",
    "quantum benchmark suite",
    "quantum chemistry algorithm comparison",
    "open source quantum benchmark"
  ],
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "QEncode - Quantum Algorithm Benchmarking Platform",
    description:
      "Open-source benchmark standard for reproducible VQE evaluation. 47 certified entries, 16 molecules. Free to run yourself. Certified results for publications.",
    url: "/"
  },
  twitter: {
    title: "QEncode - Quantum Algorithm Benchmarking Platform",
    description:
      "Open-source quantum algorithm benchmarks. Free to run. Certified results for publications."
  }
};

export default function HomePage() {
  const pillars = [
    {
      icon: BarChart3,
      title: "Fixed benchmark suite",
      desc: "Identical molecule, encoding, and ansatz settings across every submission. No setup ambiguity."
    },
    {
      icon: Shield,
      title: "Signed certified results",
      desc: "SHA-256 provenance hash and Ed25519 signature. Every certified entry is independently verifiable."
    },
    {
      icon: Trophy,
      title: "Public leaderboard",
      desc: "Compare accuracy gap, circuit depth, and two-qubit gate count across all certified submissions."
    },
    {
      icon: Database,
      title: "Fully open data",
      desc: "All benchmark entries, reference energies, and run configs published in the open GitHub repository."
    }
  ];

  const molecules = [
    { name: "H₂",    qubits: 4,  entries: 6,  certified: true  },
    { name: "HF",    qubits: 4,  entries: 6,  certified: true  },
    { name: "LiH",   qubits: 8,  entries: 3,  certified: true  },
    { name: "BeH₂",  qubits: 8,  entries: 4,  certified: true  },
    { name: "H₂O",   qubits: 8,  entries: 3,  certified: true  },
    { name: "NH₃",   qubits: 8,  entries: 3,  certified: true  },
    { name: "H₂CO",  qubits: 8,  entries: 1,  certified: true  },
    { name: "C₄H₆",  qubits: 8,  entries: 1,  certified: true  },
    { name: "(H₂O)₂", qubits: 8, entries: 4,  certified: true  },
    { name: "C₄H₄",  qubits: 8,  entries: 4,  certified: true,  badge: "CASSCF" },
    { name: "H₄",    qubits: 8,  entries: 4,  certified: true  },
    { name: "N₂",    qubits: 12, entries: 3,  certified: true,  badge: "CASSCF" },
    { name: "H₆",    qubits: 12, entries: 1,  certified: true,  badge: "CASSCF" },
    { name: "Benzene", qubits: 12, entries: 2, certified: true,  badge: "CASSCF" },
    { name: "H₈",    qubits: 16, entries: 1,  certified: true,  badge: "CASSCF" },
    { name: "H₁₀",   qubits: 20, entries: 1,  certified: true,  badge: "CASSCF" },
  ];

  return (
    <div className="min-h-screen">

      {/* ── Hero ── */}
      <section className="container pt-10 pb-16 sm:pt-16 sm:pb-20 lg:py-28">
        <div className="hidden md:block mb-8">
          <Image
            src="/logo.png"
            alt="QEncode Benchmark"
            width={140}
            height={140}
            className="h-32 w-auto"
            priority
          />
        </div>

        <div className="flex flex-wrap gap-2 mb-5">
          <Badge variant="secondary" className="text-xs font-mono">Suite v4</Badge>
          <Badge variant="secondary" className="text-xs">cc-pVDZ basis</Badge>
          <Badge variant="secondary" className="text-xs">Open source</Badge>
          <Badge variant="secondary" className="text-xs">DARPA QB-GSEE aligned</Badge>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1] mb-6 max-w-4xl">
          The open standard for quantum algorithm benchmarking.
        </h1>
        <p className="text-lg text-muted-foreground max-w-2xl mb-3">
          Quantum algorithm results are difficult to compare across papers and platforms.
          QEncode provides a fixed benchmark suite with signed certification so performance
          claims are reproducible and decision-ready.
        </p>
        <p className="text-base text-muted-foreground max-w-2xl mb-8">
          <strong className="text-foreground">Free to run yourself.</strong> Certified results available for publications and grant applications.
        </p>

        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/leaderboard" data-track="home_hero_leaderboard">
              View Leaderboard <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="secondary" size="lg">
            <Link
              href="https://github.com/qencode-benchmark/qencode-benchmark"
              target="_blank"
              rel="noopener noreferrer"
              data-track="home_hero_github"
            >
              <GitFork className="mr-1.5 h-4 w-4" /> GitHub
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/benchmark" data-track="home_hero_spec">Benchmark Spec</Link>
          </Button>
        </div>
      </section>

      {/* ── Stats bar ── */}
      <section className="border-y bg-muted/40">
        <div className="container py-8">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
            <div>
              <p className="text-3xl font-bold">47</p>
              <p className="text-sm text-muted-foreground mt-1">Certified entries</p>
            </div>
            <div>
              <p className="text-3xl font-bold">16</p>
              <p className="text-sm text-muted-foreground mt-1">Molecules in catalog</p>
            </div>
            <div>
              <p className="text-3xl font-bold">20</p>
              <p className="text-sm text-muted-foreground mt-1">Max qubits (certified)</p>
            </div>
            <div>
              <p className="text-3xl font-bold">4.5<span className="text-lg font-medium"> mHa</span></p>
              <p className="text-sm text-muted-foreground mt-1">Best gap on N₂</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Problem statement ── */}
      <section className="container py-20">
        <h2 className="text-2xl sm:text-3xl font-bold mb-4 max-w-2xl">
          Most benchmark claims are not directly comparable.
        </h2>
        <p className="text-muted-foreground text-lg max-w-2xl">
          Different molecule choices, encodings, ansatz settings, and runtime assumptions make
          cross-study comparison unreliable. Without a fixed benchmark standard, teams spend time
          arguing about setup rather than measuring quality.
        </p>
      </section>

      {/* ── Pillars ── */}
      <section className="border-t bg-muted/40">
        <div className="container py-20">
          <h2 className="text-2xl sm:text-3xl font-bold mb-10">QEncode provides</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {pillars.map((p) => (
              <Card key={p.title} className="h-full border bg-card hover:shadow-md transition-shadow">
                <CardContent className="pt-6">
                  <p.icon className="h-5 w-5 text-primary mb-3" />
                  <h3 className="font-semibold mb-1">{p.title}</h3>
                  <p className="text-sm text-muted-foreground">{p.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── Molecule catalog ── */}
      <section className="container py-20">
        <div className="flex items-end justify-between mb-8 gap-4">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold mb-2">Suite v4 molecule catalog</h2>
            <p className="text-muted-foreground">cc-pVDZ basis · active spaces are chemistry-driven · open data</p>
          </div>
          <Link
            href="/leaderboard"
            className="text-sm font-medium text-primary hover:underline shrink-0"
            data-track="home_catalog_leaderboard"
          >
            Full leaderboard →
          </Link>
        </div>

        <div className="rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 text-left">
                  <th className="px-4 py-3 font-medium text-muted-foreground">Molecule</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground text-right">Qubits (JW)</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground text-right">Certified entries</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody>
                {molecules.map((mol, i) => (
                  <tr
                    key={mol.name}
                    className={`border-t hover:bg-muted/20 transition-colors ${!mol.certified ? "opacity-60" : ""}`}
                  >
                    <td className="px-4 py-3 font-medium">
                      {mol.name}
                      {mol.badge && (
                        <Badge variant="secondary" className="ml-2 text-xs font-normal py-0">{mol.badge}</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-muted-foreground">{mol.qubits}</td>
                    <td className="px-4 py-3 text-right font-mono">
                      {mol.entries > 0 ? mol.entries : "—"}
                    </td>
                    <td className="px-4 py-3">
                      {mol.certified ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-green-700 dark:text-green-400">
                          <CheckCircle className="h-3.5 w-3.5" /> Certified
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                          <span className="h-2 w-2 rounded-full bg-muted-foreground/40 inline-block" /> Research
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="border-t bg-muted/40">
        <div className="container py-20">
          <h2 className="text-2xl sm:text-3xl font-bold mb-10">How it works</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { num: "01", title: "Run the open-source suite", desc: "Clone the repo, install requirements-v4.txt, run generate_entry_v4.py. One command per molecule." },
              { num: "02", title: "Submit or self-publish", desc: "Share your JSON entry with the community, or apply for managed certification with a signed artifact." },
              { num: "03", title: "Receive signed artifacts", desc: "QEncode runs the fixed pipeline, signs the result, and delivers a validation report." },
              { num: "04", title: "Publish or keep private", desc: "Choose public leaderboard inclusion or private delivery only for grant and paper use." }
            ].map((s) => (
              <div key={s.num}>
                <span className="font-mono text-4xl font-bold text-primary/20">{s.num}</span>
                <h3 className="font-semibold mt-2 mb-1">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Certification — soft sell ── */}
      <section className="container py-20">
        <div className="rounded-xl border bg-card p-8">
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-2xl font-bold mb-3">Need a certified result?</h2>
              <p className="text-muted-foreground mb-4">
                If you need an independently signed benchmark receipt for a paper, grant, or
                hardware evaluation, QEncode offers managed certification with full provenance.
                The self-run path is always free.
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild>
                  <Link href="/apply" data-track="home_cert_apply">Apply for certification</Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href="/pricing" data-track="home_cert_pricing">See pricing</Link>
                </Button>
              </div>
            </div>
            <div className="space-y-3 text-sm">
              {[
                "SHA-256 provenance hash on every certified entry",
                "Ed25519 signature — independently verifiable",
                "CASCI reference energy from PySCF",
                "Public or private delivery — your choice",
                "Audit-ready report package included"
              ].map((item) => (
                <div key={item} className="flex items-start gap-2 text-muted-foreground">
                  <CheckCircle className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="border-t bg-muted/40">
        <div className="container py-20 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">
            Start benchmarking — it&apos;s free and open source.
          </h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Clone the repo, run the suite, and join the leaderboard.
            Certification available when you need signed results.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="lg">
              <Link
                href="https://github.com/qencode-benchmark/qencode-benchmark"
                target="_blank"
                rel="noopener noreferrer"
                data-track="home_bottom_github"
              >
                <GitFork className="mr-1.5 h-4 w-4" /> Get started on GitHub
              </Link>
            </Button>
            <Button asChild variant="secondary" size="lg">
              <Link href="/leaderboard" data-track="home_bottom_leaderboard">View Leaderboard</Link>
            </Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/blog" data-track="home_bottom_blog">Read the blog</Link>
            </Button>
          </div>
        </div>
      </section>

    </div>
  );
}
