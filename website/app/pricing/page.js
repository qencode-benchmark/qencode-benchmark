import Link from "next/link";
import { CheckCircle2, Clock3, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata = {
  title: "Pricing and Certification Plans",
  description:
    "Review QEncode pricing for single-molecule and full-suite quantum benchmark certification, including managed execution and signed artifact delivery.",
  keywords: [
    "quantum benchmark pricing",
    "quantum certification pricing",
    "single molecule certification",
    "full suite certification"
  ],
  alternates: {
    canonical: "/pricing"
  },
  openGraph: {
    title: "QEncode Pricing - Quantum Benchmark Certification",
    description:
      "Choose certification scope, apply for access, and launch managed quantum benchmark execution.",
    url: "/pricing"
  }
};

export default function PricingPage() {
  return (
    <div className="container py-16">
      <h1 className="text-3xl sm:text-4xl font-bold mb-3">Pricing</h1>
      <p className="text-muted-foreground max-w-3xl mb-8">
        QEncode uses an access-first model: choose your certification scope, then submit an access application for
        managed execution and private benchmarking workflows.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border">
          <CardHeader>
            <CardTitle>Single Molecule Certification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$1,500</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Managed benchmark execution for one Suite v2 molecule.</li>
              <li className="flex gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Signed receipt + validation report package.</li>
              <li className="flex gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Public leaderboard eligibility when quality criteria pass.</li>
            </ul>
            <div className="flex flex-wrap gap-2">
              <Button asChild><Link href="/certify" data-track="pricing_single_buy_now">Buy now</Link></Button>
              <Button asChild variant="outline"><Link href="/apply" data-track="pricing_single_apply_access">Apply for access</Link></Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border">
          <CardHeader>
            <CardTitle>Full Suite v2 Certification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$4,000</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Full managed execution across Suite v2 scope.</li>
              <li className="flex gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Signed artifacts + audit-ready benchmark package.</li>
              <li className="flex gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Strongest trust signal for external publication.</li>
            </ul>
            <div className="flex flex-wrap gap-2">
              <Button asChild><Link href="/certify" data-track="pricing_full_buy_now">Buy now</Link></Button>
              <Button asChild variant="outline"><Link href="/apply" data-track="pricing_full_apply_access">Apply for access</Link></Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <section className="mt-8 rounded-lg border p-5">
        <h2 className="text-xl font-semibold mb-3">Access pipeline</h2>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1"><Clock3 className="h-4 w-4 text-primary" /> 1. Apply</div>
            <p className="text-muted-foreground">Submit workload scope and timeline in the access form.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1"><ShieldCheck className="h-4 w-4 text-primary" /> 2. Scope review</div>
            <p className="text-muted-foreground">QEncode confirms plan fit, runtime class, and expected turnaround.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1"><CheckCircle2 className="h-4 w-4 text-primary" /> 3. Execute</div>
            <p className="text-muted-foreground">Managed run + signed artifact delivery and publication options.</p>
          </div>
        </div>
      </section>

      <section className="mt-8 rounded-lg border p-5">
        <h2 className="text-xl font-semibold mb-3">FAQ</h2>
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium">Is benchmark access free?</h3>
            <p className="text-muted-foreground">Early access is free for qualifying teams; certification services are paid.</p>
          </div>
          <div>
            <h3 className="font-medium">Do we need to pay before applying?</h3>
            <p className="text-muted-foreground">No. Apply first so QEncode can confirm scope, readiness, and turnaround.</p>
          </div>
          <div>
            <h3 className="font-medium">Can results stay private?</h3>
            <p className="text-muted-foreground">Yes. Public leaderboard publication is optional unless explicitly requested.</p>
          </div>
        </div>
      </section>

      <section className="mt-8 rounded-lg border p-5">
        <h2 className="text-xl font-semibold mb-3">Join waitlist</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Prefer to start with free early access? Share your email and we will invite eligible teams in rollout order.
        </p>
        <form
          className="flex flex-col sm:flex-row gap-3"
          action="mailto:support@qencode-benchmark.org"
          method="post"
          encType="text/plain"
        >
          <input
            name="email"
            type="email"
            required
            placeholder="you@company.com"
            className="sm:max-w-sm w-full rounded-md border bg-background px-3 py-2 text-sm"
          />
          <input name="subject" type="hidden" value="QEncode waitlist request" />
          <Button type="submit" data-track="pricing_waitlist_submit">Join Waitlist</Button>
        </form>
      </section>
    </div>
  );
}

