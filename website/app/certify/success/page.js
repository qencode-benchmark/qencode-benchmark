import Link from "next/link";
import { CheckCircle2, Clock3, ShieldCheck, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata = {
  title: "Order Confirmed",
  description: "Your QEncode certification order is confirmed. Check your email for next steps.",
  alternates: {
    canonical: "/certify/success"
  },
  robots: {
    index: false,
    follow: false
  }
};

const supportEmail = "support@qencode-benchmark.org";

export default function CertifySuccessPage() {
  return (
    <div className="container py-16">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-verified/15 text-verified mb-3">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <CardTitle>Order confirmed</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6 text-sm text-muted-foreground">
          <p>
            Your payment has been received. A confirmation email with your order details and next steps
            has been sent to your billing email address.
          </p>

          {/* Timeline */}
          <div className="space-y-3">
            <div className="flex items-start gap-3 rounded-md border p-3">
              <Mail className="h-4 w-4 mt-0.5 text-primary shrink-0" />
              <div>
                <p className="font-medium text-foreground">Check your inbox</p>
                <p>A confirmation email has been sent to the email you used at checkout. It contains your order summary and what to expect.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-md border p-3">
              <Clock3 className="h-4 w-4 mt-0.5 text-primary shrink-0" />
              <div>
                <p className="font-medium text-foreground">Intake within 1 business day</p>
                <p>Our team will review your order and send a follow-up to confirm job scheduling and any details we need.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-md border p-3">
              <ShieldCheck className="h-4 w-4 mt-0.5 text-primary shrink-0" />
              <div>
                <p className="font-medium text-foreground">Artifacts in 5–10 business days</p>
                <p>Signed certification receipt, validation summary, and leaderboard eligibility determination delivered by email.</p>
              </div>
            </div>
          </div>

          <p className="text-xs">
            Didn&apos;t receive a confirmation email? Check your spam folder or contact{" "}
            <a href={`mailto:${supportEmail}`} className="text-foreground underline underline-offset-2">
              {supportEmail}
            </a>{" "}
            with your order number.
          </p>

          <div className="flex flex-wrap gap-3 pt-1">
            <Button asChild variant="outline">
              <Link href="/leaderboard">View Leaderboard</Link>
            </Button>
            <Button asChild variant="ghost">
              <Link href="/certify">Back to pricing</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
