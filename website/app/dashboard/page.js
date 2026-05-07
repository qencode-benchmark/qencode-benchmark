import Link from "next/link";

export const metadata = {
  title: "Dashboard | QEncode",
};

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-background">
      <div className="border-b">
        <div className="container flex h-14 items-center">
          <Link href="/" className="font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors">
            ← Back to QEncode
          </Link>
        </div>
      </div>
      <div className="container py-20 max-w-2xl text-center">
        <p className="text-sm font-medium text-primary mb-3 uppercase tracking-wide">Dashboard</p>
        <h1 className="text-3xl font-bold mb-4">Order tracking coming soon</h1>
        <p className="text-muted-foreground mb-8">
          Your certification orders and benchmark results are delivered directly to your registered email.
          Contact support to check on an order status.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            href="/apply"
            className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          >
            Apply for Access
          </Link>
          <a
            href="mailto:support@qencode-benchmark.org"
            className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
          >
            support@qencode-benchmark.org
          </a>
        </div>
      </div>
    </main>
  );
}
