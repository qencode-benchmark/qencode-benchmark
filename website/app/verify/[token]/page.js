import { getCertificationByToken } from "@/lib/db";
import Link from "next/link";
import { CheckCircle2, XCircle, ShieldCheck } from "lucide-react";

export const dynamic = "force-dynamic";

function formatDate(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });
}

function formatType(type) {
  if (type === "full_suite") return "Full Suite v2 (5 molecules)";
  if (type === "single_molecule") return "Single Molecule";
  return type ?? "—";
}

export async function generateMetadata({ params }) {
  const { token } = await params;
  return {
    title: `Certification Verification · ${token.slice(0, 8)}`,
    description: "Verify a QEncode benchmark certification receipt.",
    robots: { index: false },
  };
}

export default async function VerifyPage({ params }) {
  const { token } = await params;

  // Validate UUID format before hitting DB
  const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  const validFormat = UUID_RE.test(token);

  let cert = null;
  if (validFormat) {
    try {
      cert = await getCertificationByToken(token);
    } catch {
      // DB unreachable — show error state
    }
  }

  const SITE_URL = "https://www.qencode-benchmark.org";
  const badgeUrl  = `${SITE_URL}/api/badge/${token}`;
  const verifyUrl = `${SITE_URL}/verify/${token}`;

  return (
    <main className="container max-w-2xl py-16">
      <Link href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← QEncode
      </Link>

      <div className="mt-10">
        {cert ? (
          /* ── Valid certification ─────────────────────────────────────────── */
          <div>
            <div className="flex items-center gap-3 mb-6">
              <CheckCircle2 className="h-8 w-8 text-green-500 shrink-0" />
              <div>
                <h1 className="text-2xl font-semibold text-foreground">Certification verified</h1>
                <p className="text-sm text-muted-foreground">
                  This certification receipt is authentic and on record with QEncode.
                </p>
              </div>
            </div>

            {/* Details card */}
            <div className="rounded-lg border bg-card p-6 space-y-4 mb-8">
              <div className="grid grid-cols-2 gap-y-4 text-sm">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Order</p>
                  <p className="font-medium text-foreground">#{cert.ls_order_number}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Product</p>
                  <p className="font-medium text-foreground">{cert.product_label}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Scope</p>
                  <p className="font-medium text-foreground">{formatType(cert.product_type)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Status</p>
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-green-100 text-green-800 px-2.5 py-0.5 text-xs font-medium">
                    <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
                    Completed
                  </span>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Ordered</p>
                  <p className="font-medium text-foreground">{formatDate(cert.created_at)}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Certified</p>
                  <p className="font-medium text-foreground">{formatDate(cert.completed_at)}</p>
                </div>
                {cert.customer_name && (
                  <div className="col-span-2">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Issued to</p>
                    <p className="font-medium text-foreground">{cert.customer_name}</p>
                  </div>
                )}
              </div>

              <div className="border-t pt-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
                  Certification token
                </p>
                <code className="text-xs font-mono text-foreground/70 break-all">{token}</code>
              </div>
            </div>

            {/* Badge embed instructions */}
            <div className="rounded-lg border bg-muted/40 p-5 mb-8">
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheck className="h-4 w-4 text-muted-foreground" />
                <p className="text-sm font-medium text-foreground">Add this badge to your GitHub README</p>
              </div>
              {/* Preview */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={badgeUrl} alt="QEncode Certified" className="mb-3" />
              <pre className="text-xs bg-background rounded border p-3 overflow-x-auto text-foreground/70 whitespace-pre-wrap break-all">
{`[![QEncode Certified](${badgeUrl})](${verifyUrl})`}
              </pre>
              <p className="mt-2 text-xs text-muted-foreground">
                Anyone who clicks the badge is taken to this verification page.
              </p>
            </div>

            <div className="flex gap-3 flex-wrap">
              <Link
                href="/leaderboard"
                className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
              >
                View leaderboard
              </Link>
              <Link
                href="/benchmark"
                className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
              >
                Benchmark spec
              </Link>
            </div>
          </div>
        ) : (
          /* ── Not found ───────────────────────────────────────────────────── */
          <div>
            <div className="flex items-center gap-3 mb-6">
              <XCircle className="h-8 w-8 text-red-500 shrink-0" />
              <div>
                <h1 className="text-2xl font-semibold text-foreground">
                  {validFormat ? "Certification not found" : "Invalid certification token"}
                </h1>
                <p className="text-sm text-muted-foreground">
                  {validFormat
                    ? "No completed certification matches this token. It may be invalid, revoked, or not yet completed."
                    : "The token in this URL is not in a valid format."}
                </p>
              </div>
            </div>
            <div className="rounded-lg border bg-muted/40 p-5 mb-8">
              <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Token presented</p>
              <code className="text-xs font-mono text-foreground/70 break-all">{token}</code>
            </div>
            <p className="text-sm text-muted-foreground mb-6">
              If you believe this is an error, contact{" "}
              <a href="mailto:support@qencode-benchmark.org" className="underline text-foreground">
                support@qencode-benchmark.org
              </a>{" "}
              with your order number.
            </p>
            <Link
              href="/"
              className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
            >
              Back to QEncode
            </Link>
          </div>
        )}
      </div>
    </main>
  );
}
