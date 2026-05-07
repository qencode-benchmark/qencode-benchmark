import { auth, currentUser } from "@clerk/nextjs/server";
import { getOrdersByEmail } from "@/lib/db";
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

export const dynamic = "force-dynamic";

const STATUS_CONFIG = {
  pending:   { label: "Queued",     color: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400" },
  running:   { label: "Running",    color: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400" },
  completed: { label: "Completed",  color: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" },
  failed:    { label: "Failed",     color: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-muted text-muted-foreground" };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.color}`}>
      {status === "running" && (
        <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
      )}
      {cfg.label}
    </span>
  );
}

function formatDate(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
  });
}

export default async function DashboardPage() {
  const { userId } = await auth();
  const user = await currentUser();

  const email = user?.emailAddresses?.[0]?.emailAddress ?? null;

  let orders = [];
  if (email) {
    try {
      orders = await getOrdersByEmail(email);
    } catch {
      // DB not configured or unreachable — show empty state
    }
  }

  const firstName = user?.firstName ?? user?.username ?? "there";

  return (
    <main className="min-h-screen bg-background">
      {/* Top bar */}
      <div className="border-b">
        <div className="container flex h-14 items-center justify-between">
          <Link href="/" className="font-semibold text-sm text-muted-foreground hover:text-foreground transition-colors">
            ← Back to QEncode
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground hidden sm:block">{email}</span>
            <UserButton afterSignOutUrl="/" />
          </div>
        </div>
      </div>

      <div className="container py-12 max-w-3xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Welcome back, {firstName}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track your certification orders and results below.
          </p>
        </div>

        {/* Orders */}
        {orders.length === 0 ? (
          <div className="rounded-lg border border-dashed p-12 text-center">
            <p className="text-sm font-medium text-foreground">No orders yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Once you purchase a certification, it will appear here.
            </p>
            <Link
              href="/pricing"
              className="mt-4 inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              View pricing
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <div key={order.id} className="rounded-lg border bg-card p-6">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <p className="font-medium text-foreground">{order.product_label}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      Order #{order.ls_order_number} &nbsp;·&nbsp; {order.total_formatted}
                    </p>
                  </div>
                  <StatusBadge status={order.status} />
                </div>

                {/* Timeline */}
                <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-muted-foreground border-t pt-4">
                  <div>
                    <p className="font-medium text-foreground/60 uppercase tracking-wide text-[10px] mb-0.5">Ordered</p>
                    <p>{formatDate(order.created_at)}</p>
                  </div>
                  <div>
                    <p className="font-medium text-foreground/60 uppercase tracking-wide text-[10px] mb-0.5">Started</p>
                    <p>{formatDate(order.started_at)}</p>
                  </div>
                  <div>
                    <p className="font-medium text-foreground/60 uppercase tracking-wide text-[10px] mb-0.5">Completed</p>
                    <p>{formatDate(order.completed_at)}</p>
                  </div>
                </div>

                {/* Notes / error */}
                {order.status === "completed" && order.notes && (
                  <p className="mt-3 text-xs text-muted-foreground border-t pt-3">
                    {order.notes}
                  </p>
                )}
                {order.status === "failed" && order.error_message && (
                  <p className="mt-3 text-xs text-red-600 border-t pt-3">
                    Error: {order.error_message}
                  </p>
                )}

                {/* Completed CTA */}
                {order.status === "completed" && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-xs text-muted-foreground">
                      Your signed certification receipt and results have been sent to <strong>{email}</strong>.
                      Check your inbox or contact{" "}
                      <a href="mailto:support@qencode-benchmark.org" className="underline">
                        support@qencode-benchmark.org
                      </a>
                      .
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Help */}
        <p className="mt-8 text-center text-xs text-muted-foreground">
          Questions about your order?{" "}
          <a href="mailto:support@qencode-benchmark.org" className="underline">
            support@qencode-benchmark.org
          </a>
        </p>
      </div>
    </main>
  );
}
