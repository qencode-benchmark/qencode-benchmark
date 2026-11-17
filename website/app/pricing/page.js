import Link from "next/link";
import { CheckCircle2, Clock3, ShieldCheck, GitFork } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OpenResearchTier, SameCriteriaNote } from "@/components/OpenResearchTier";

export const metadata = {
  title: "Pricing and Certification",
  description:
    "QEncode is free to run yourself, and managed certification is free for open academic research. Companies and private results use the paid plans. Same criteria for every run.",
  keywords: [
    "quantum benchmark pricing",
    "quantum certification pricing",
    "free academic quantum benchmark",
    "single molecule certification",
    "full suite certification"
  ],
  alternates: {
    canonical: "/pricing"
  },
  openGraph: {
    title: "QEncode Pricing - Quantum Benchmark Certification",
    description:
      "Run QEncode free. Managed certification is free for open academic research; paid plans for companies.",
    url: "https://www.qencode-benchmark.org/pricing"
  }
};

export default function PricingPage() {
  return (
    <div className="container py-16 max-w-4xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-3">Pricing</h1>
      <p className="text-muted-foreground max-w-2xl mb-2 text-lg">
        The benchmark suite is <strong className="text-foreground">free and open source</strong>. Run it yourself with one command.
      </p>
      <p className="text-muted-foreground max-w-2xl mb-10">
        Managed certification — a signed entry, provenance hash and validation report — is{" "}
        <strong className="text-foreground">free for open academic research</strong>. Companies, commercial
        work and results kept private use the paid plans.
      </p>

      {/* Free path callout */}
      <div className="rounded-lg border bg-muted/40 p-6 mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="font-semibold text-lg mb-1">Self-run — always free</h2>
          <p className="text-sm text-muted-foreground">
            Clone the repo, install requirements-v4.txt, and run{" "}
            <code className="font-mono text-xs bg-background border rounded px-1.5 py-0.5">generate_entry_v4.py</code>.
            Full pipeline: PySCF → PennyLane → VQE → JSON entry.
          </p>
        </div>
        <Button asChild variant="secondary" className="shrink-0">
          <Link
            href="https://github.com/qencode-benchmark/qencode-benchmark"
            target="_blank"
            rel="noopener noreferrer"
            data-track="pricing_github"
          >
            <GitFork className="mr-1.5 h-4 w-4" /> GitHub
          </Link>
        </Button>
      </div>

      <OpenResearchTier trackPrefix="pricing" />

      {/* Managed certification plans */}
      <h2 className="text-xl font-semibold mb-1">Companies and private results</h2>
      <p className="text-sm text-muted-foreground mb-4">
        For commercial use, company-funded work, or results that stay private.
      </p>
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card className="border">
          <CardHeader>
            <CardTitle>Single Molecule</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$1,500</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Managed benchmark execution for one Suite v4 molecule.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Signed receipt + validation report package.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Public leaderboard eligibility when quality criteria pass.
              </li>
            </ul>
            <Button asChild>
              <Link href="/apply?type=commercial" data-track="pricing_single_apply">Apply for access</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border">
          <CardHeader>
            <CardTitle>Full Suite v4</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$4,000</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Full managed execution across all Suite v4 molecules.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Signed artifacts + audit-ready benchmark package.
              </li>
              <li className="flex gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                One package covering all 16 molecules, for hardware or algorithm comparisons.
              </li>
            </ul>
            <Button asChild>
              <Link href="/apply?type=commercial" data-track="pricing_full_apply">Apply for access</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <SameCriteriaNote />

      {/* Access pipeline */}
      <section className="rounded-lg border p-5 mb-6">
        <h2 className="text-xl font-semibold mb-3">How certification works</h2>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1">
              <Clock3 className="h-4 w-4 text-primary shrink-0" /> 1. Apply
            </div>
            <p className="text-muted-foreground">Submit workload scope and timeline in the access form.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1">
              <ShieldCheck className="h-4 w-4 text-primary shrink-0" /> 2. Scope review
            </div>
            <p className="text-muted-foreground">QEncode confirms plan fit, runtime class, and expected turnaround.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1">
              <CheckCircle2 className="h-4 w-4 text-primary shrink-0" /> 3. Execute & deliver
            </div>
            <p className="text-muted-foreground">Managed run + signed artifact delivery and publication options.</p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="rounded-lg border p-5 mb-6">
        <h2 className="text-xl font-semibold mb-3">FAQ</h2>
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium">Is benchmark access free?</h3>
            <p className="text-muted-foreground">Yes — the full suite is open source. Run it yourself for free anytime. Managed certification is free for open academic research and paid for companies and private results.</p>
          </div>
          <div>
            <h3 className="font-medium">Who qualifies for the free open-research tier?</h3>
            <p className="text-muted-foreground">
              Researchers at universities, public research institutes and non-profits, for work whose results
              will be published openly on the leaderboard. If a company funds the work or owns the results, or the
              results must stay private, the paid plans apply. Places are limited each month.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Do we need to pay before applying?</h3>
            <p className="text-muted-foreground">No. Apply first so QEncode can confirm scope, readiness, and turnaround.</p>
          </div>
          <div>
            <h3 className="font-medium">Can results stay private?</h3>
            <p className="text-muted-foreground">On the paid plans, yes — public leaderboard publication is optional and private delivery is fully supported. Free open-research runs are always published.</p>
          </div>
          <div>
            <h3 className="font-medium">What molecules are available in Suite v4?</h3>
            <p className="text-muted-foreground">
              H₂, HF, LiH, BeH₂, H₂O, NH₃, H₂CO, C₄H₆, (H₂O)₂, C₄H₄, H₄, N₂, H₆, benzene, H₈, and H₁₀ — all certified.
              All use cc-pVDZ basis with chemistry-driven active spaces.
            </p>
          </div>
        </div>
      </section>

      {/* Contact CTA */}
      <section className="rounded-lg border p-5">
        <h2 className="text-xl font-semibold mb-2">Questions?</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Reach out directly — we&apos;ll help you choose the right scope for your timeline and budget.
        </p>
        <Button asChild variant="outline">
          <a href="mailto:support@qencode-benchmark.org" data-track="pricing_contact_email">
            support@qencode-benchmark.org
          </a>
        </Button>
      </section>
    </div>
  );
}
