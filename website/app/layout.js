import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import Navbar from "@/components/Navbar";
import AnalyticsClickTracker from "@/components/AnalyticsClickTracker";
import { Analytics } from "@vercel/analytics/next";
import Link from "next/link";

const SITE_URL = "https://www.qencode-benchmark.org";
const SITE_NAME = "QEncode";
const DEFAULT_TITLE = "QEncode - The Standard for Quantum Algorithm Benchmarking";
const DEFAULT_DESCRIPTION =
  "QEncode is the quantum algorithm benchmarking standard for reproducible VQE evaluation, managed execution, signed certification, and public leaderboard comparison.";

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: DEFAULT_TITLE,
    template: "%s | QEncode"
  },
  description: DEFAULT_DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: [
    "quantum algorithm benchmarking",
    "quantum chemistry benchmark",
    "VQE benchmark",
    "quantum leaderboard",
    "quantum algorithm certification",
    "reproducible quantum benchmarks"
  ],
  alternates: {
    canonical: "/"
  },
  robots: {
    index: true,
    follow: true
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION
  },
  twitter: {
    card: "summary_large_image",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION
  }
};

export default function RootLayout({ children }) {
  const REPO_URL = "https://github.com/qencode-benchmark/qencode-benchmark";
  const organizationSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: SITE_URL,
    email: "support@qencode-benchmark.org",
    sameAs: [REPO_URL]
  };
  return (
    <ClerkProvider>
    <html lang="en">
      <body>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
        />
        <AnalyticsClickTracker />
        <Analytics />
        <Navbar />
        {children}
        <footer className="border-t mt-16">
          <div className="container py-10 text-sm text-muted-foreground grid gap-8 md:grid-cols-3">
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Platform</h3>
              <div className="flex flex-col gap-1">
                <Link href="/leaderboard">Leaderboard</Link>
                <Link href="/benchmark">Benchmark Spec</Link>
                <Link href="/pricing">Pricing</Link>
                <Link href="/blog">Blog</Link>
                <Link href="/apply">Apply for Access</Link>
                <Link href="/docs">Docs</Link>
              </div>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Resources</h3>
              <div className="flex flex-col gap-1">
                <Link href="/docs">Whitepaper (PDF)</Link>
                <Link href="/docs">Benchmark Specification (PDF)</Link>
                <Link href="/docs">Leaderboard Rules</Link>
                <a href={REPO_URL} target="_blank" rel="noopener noreferrer">GitHub</a>
              </div>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Company</h3>
              <div className="flex flex-col gap-1">
                <Link href="/about">About</Link>
                <a href="mailto:support@qencode-benchmark.org">support@qencode-benchmark.org</a>
                <span>Citation: CITATION.cff</span>
                <span>&copy; 2026 QEncode. Suite v2.</span>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
    </ClerkProvider>
  );
}

