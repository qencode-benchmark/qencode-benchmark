import Link from "next/link";
import { CheckCircle2, Clock3, ShieldCheck, FlaskConical, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Direct checkout is paused: until fulfilment is rebuilt for Suite v4, every order starts
// with an application, so nothing is sold that cannot be delivered. lib/payments.js keeps
// the Lemon Squeezy URLs for when checkout returns.

export const metadata = {
  title: "Get Certified — QEncode",
  description:
    "Apply for QEncode managed quantum benchmark certification for a single molecule or full Suite v4 and receive signed artifacts for publications, grants, and hardware evaluations.",
  keywords: [
    "quantum benchmark certification",
    "QEncode certification",
    "signed benchmark receipt",
    "suite v4 certification"
  ],
  alternates: { canonical: "/certify" },
  openGraph: {
    title: "Get Certified — QEncode",
    description:
      "Managed certification with signed artifacts for quantum algorithm results. Suite v4, cc-pVDZ basis.",
    url: "https://www.qencode-benchmark.org/certify"
  }
};

const supportEmail = "support@qencode-benchmark.org";

export default function CertifyPage() {
  return (
    <div className="container py-16 max-w-4xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-3">Get Certified</h1>
      <p className="text-muted-foreground max-w-2xl mb-4">
        Managed certification provides a signed artifact, provenance receipt, and audit-ready benchmark
        report — suitable for papers, grant applications, and hardware evaluation claims.
      </p>

      {/* Apply-first callout */}
      <div className="rounded-lg border border-primary/30 bg-primary/5 p-5 mb-10">
        <p className="font-medium mb-1">Certification starts with a short application.</p>
        <p className="text-sm text-muted-foreground mb-3">
          Tell us the molecules, active space requirements and timeline. We confirm the scope and
          the right plan with you, and agree payment, before any run starts.
          The application takes 2 minutes and we respond within 1–2 business days.
        </p>
        <Link
          href="/apply"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          data-track="certify_apply_first_cta"
        >
          Apply for certification <ArrowRight className="h-4 w-4 shrink-0" />
        </Link>
      </div>

      {/* Plans */}
      <h2 className="text-xl font-semibold mb-4">Certification plans</h2>
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card className="border">
          <CardHeader>
            <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary mb-3">
              <FlaskConical className="h-5 w-5" />
            </div>
            <CardTitle>Single Molecule</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$1,500</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Managed benchmark execution for one Suite v4 molecule.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Signed certification receipt + benchmark report.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Public leaderboard eligibility when quality criteria pass.
              </li>
            </ul>
            <Button asChild className="w-full">
              <Link href="/apply" data-track="certify_single_apply_click">
                Apply — Single Molecule
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border">
          <CardHeader>
            <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary mb-3">
              <ShieldCheck className="h-5 w-5 shrink-0" />
            </div>
            <CardTitle>Full Suite v4</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$4,000</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Managed execution across the full Suite v4 molecule catalog.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Signed artifacts + audit-ready benchmark package.
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
                Strongest trust signal for external publication or hardware evaluation.
              </li>
            </ul>
            <Button asChild className="w-full">
              <Link href="/apply" data-track="certify_full_apply_click">
                Apply — Full Suite v4
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Service level */}
      <section className="rounded-lg border p-5 mb-6">
        <h2 className="text-xl font-semibold mb-3">Service level and delivery</h2>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1">
              <Clock3 className="h-4 w-4 text-primary shrink-0" /> Intake confirmation
            </div>
            <p className="text-muted-foreground">Within 1–2 business days of your application.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1">
              <ShieldCheck className="h-4 w-4 text-primary shrink-0" /> Standard turnaround
            </div>
            <p className="text-muted-foreground">5–10 business days depending on queue and compute load.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1">
              <CheckCircle2 className="h-4 w-4 text-primary shrink-0" /> Delivery artifacts
            </div>
            <p className="text-muted-foreground">Signed receipt, validation summary, and leaderboard eligibility determination.</p>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="rounded-lg border p-5 mb-6">
        <h2 className="text-xl font-semibold mb-3">FAQ</h2>
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium">If the benchmark is open-source, why pay?</h3>
            <p className="text-muted-foreground">
              Anyone can run the code — that is the point. The certification service provides managed
              execution, Ed25519-signed artifacts, and an audit-ready report that reviewers, program
              officers, and hardware vendors can independently verify. Self-run results are valid for
              research; signed certified results are required for leaderboard inclusion and external claims.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Is the fee charged even if I don&apos;t pass certification?</h3>
            <p className="text-muted-foreground">
              Yes — the fee covers managed execution, audit work, and verification regardless of outcome.
              Failed runs appear in the Research tab, not the trash. If a molecule doesn&apos;t converge,
              we record and deliver the result as-is.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Can results stay private?</h3>
            <p className="text-muted-foreground">
              Yes. Public leaderboard inclusion is optional — private delivery is fully supported for
              internal R&D, competitive benchmarking, and grant use.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Which molecules are available?</h3>
            <p className="text-muted-foreground">
              All Suite v4 molecules: H₂, HF, LiH, BeH₂, H₂O, NH₃, H₂CO, C₄H₆, (H₂O)₂, C₄H₄, H₄, N₂, H₆,
              benzene, H₈, and H₁₀ — all certified. Custom molecules available on request — contact us to discuss scope.
            </p>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-3">
        <Link href="/apply" className="text-sm text-primary hover:underline" data-track="certify_apply_link_bottom">
          Apply for certification →
        </Link>
        <span className="text-sm text-muted-foreground">or</span>
        <a href={`mailto:${supportEmail}`} className="text-sm text-primary hover:underline">
          {supportEmail}
        </a>
      </div>
    </div>
  );
}
