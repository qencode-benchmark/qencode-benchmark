import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Certification Checkout Canceled",
  description: "Return to QEncode certification pricing and continue your checkout anytime.",
  alternates: {
    canonical: "/certify/cancel"
  },
  robots: {
    index: false,
    follow: false
  }
};

export default function CertifyCancelPage() {
  return (
    <div className="container py-16 max-w-2xl">
      <h1 className="text-3xl font-bold mb-3">Checkout canceled</h1>
      <p className="text-muted-foreground mb-6">
        No worries. You can return to certification pricing and continue anytime.
      </p>
      <div className="flex flex-wrap gap-3">
        <Button asChild>
          <Link href="/certify">Return to Get Certified</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/docs">Read Docs First</Link>
        </Button>
      </div>
    </div>
  );
}

