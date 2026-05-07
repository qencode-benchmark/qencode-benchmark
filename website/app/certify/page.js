import Link from "next/link";
import { CheckCircle2, Clock3, ShieldCheck, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LS_FULL_SUITE_CHECKOUT_URL, LS_SINGLE_MOLECULE_CHECKOUT_URL } from "@/lib/payments";

export const metadata = {
  title: "Get Certified",
  description:
    "Purchase QEncode quantum benchmark certification for a single molecule or full Suite v2 and receive signed verification artifacts for reproducible claims.",
  keywords: [
    "quantum benchmark certification",
    "QEncode certification",
    "Lemon Squeezy checkout quantum",
    "signed benchmark receipt"
  ],
  alternates: {
    canonical: "/certify"
  },
  openGraph: {
    title: "Get Certified - QEncode",
    description:
      "Start official certification with managed benchmark execution and signed artifact delivery.",
    url: "/certify"
  }
};

const supportEmail = "support@qencode-benchmark.org";

export default function CertifyPage() {
  return (
    <div className="container py-16">
      <h1 className="text-3xl sm:text-4xl font-bold mb-3">Get Certified</h1>
      <p className="text-muted-foreground max-w-2xl mb-8">
        Purchase an official QEncode certification request. After payment, follow the submission steps on the success page
        to send your benchmark details for processing.
      </p>
      <p className="text-sm text-muted-foreground mb-8">
        Open-source benchmark, paid official trust layer: anyone can run locally, but only official signed receipts are
        accepted for certified public leaderboard inclusion.
      </p>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="border">
          <CardHeader>
            <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary mb-3">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <CardTitle>Full Suite v2 Certification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$4,000</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Hosted compute + certification for full Suite v2 scope.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Signed certification receipt and audit-ready artifacts.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Eligible for official public dataset inclusion when rules are met.</li>
            </ul>
            <Button asChild className="w-full">
              <a href={LS_FULL_SUITE_CHECKOUT_URL} target="_blank" rel="noopener noreferrer" data-track="certify_full_checkout_click">
                Buy Full Suite Certification
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card className="border">
          <CardHeader>
            <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary mb-3">
              <FlaskConical className="h-5 w-5" />
            </div>
            <CardTitle>Single-Molecule Certification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-3xl font-bold">$1,500</p>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Hosted compute + certification for one molecule in Suite v2.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Signed certification receipt and benchmark report.</li>
              <li className="flex items-start gap-2"><CheckCircle2 className="h-4 w-4 mt-0.5 text-verified" /> Fastest path to validate one target benchmark request.</li>
            </ul>
            <Button asChild className="w-full" variant="outline">
              <a href={LS_SINGLE_MOLECULE_CHECKOUT_URL} target="_blank" rel="noopener noreferrer" data-track="certify_single_checkout_click">
                Buy Single-Molecule Certification
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 rounded-lg border p-4 text-sm text-muted-foreground">
        After checkout completes, open <code>/certify/success</code> and email your submission details to{" "}
        <a href={`mailto:${supportEmail}`} className="text-primary underline underline-offset-2">{supportEmail}</a>.
      </div>

      <section className="mt-8 rounded-lg border p-5">
        <h2 className="text-xl font-semibold mb-3">Service Level and Delivery</h2>
        <div className="grid gap-4 sm:grid-cols-3 text-sm">
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1"><Clock3 className="h-4 w-4 text-primary" /> Intake confirmation</div>
            <p className="text-muted-foreground">Within 1 business day after payment and request details.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1"><ShieldCheck className="h-4 w-4 text-primary" /> Standard turnaround</div>
            <p className="text-muted-foreground">5-10 business days depending on queue and compute load.</p>
          </div>
          <div className="rounded-md bg-muted/50 p-3">
            <div className="flex items-center gap-2 font-medium mb-1"><CheckCircle2 className="h-4 w-4 text-primary" /> Delivery artifacts</div>
            <p className="text-muted-foreground">Receipt, validation summary, and eligibility determination.</p>
          </div>
        </div>
      </section>

      <section className="mt-8 rounded-lg border p-5">
        <h2 className="text-xl font-semibold mb-3">FAQ</h2>
        <div className="space-y-4 text-sm">
          <div>
            <h3 className="font-medium">If the benchmark is open-source, why pay?</h3>
            <p className="text-muted-foreground">
              Anyone can run the code, but only QEncode can issue official signed receipts accepted for certified public
              leaderboard inclusion.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Do I pay only if I pass certification?</h3>
            <p className="text-muted-foreground">
              Certification is paid as a service attempt. The fee covers managed execution, audit work, and verification
              regardless of outcome.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Can I keep my results private?</h3>
            <p className="text-muted-foreground">
              Yes. Public release is optional unless you request leaderboard publication.
            </p>
          </div>
        </div>
      </section>

      <div className="mt-6">
        <Link href="/docs" className="text-sm text-primary underline underline-offset-2">
          Read docs before purchasing
        </Link>
      </div>
    </div>
  );
}

