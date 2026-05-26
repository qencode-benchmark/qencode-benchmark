import "./globals.css";
import Navbar from "@/components/Navbar";
import AnalyticsClickTracker from "@/components/AnalyticsClickTracker";
import { Analytics } from "@vercel/analytics/next";
import Link from "next/link";
import Image from "next/image";

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
  icons: {
    icon: "/logo.png",
    shortcut: "/logo.png",
    apple: "/logo.png"
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: SITE_URL,
    siteName: SITE_NAME,
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
    images: [{ url: "/logo.png", width: 512, height: 512, alt: "QEncode Benchmark" }]
  },
  twitter: {
    card: "summary_large_image",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
    images: ["/logo.png"]
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
                <Link href="/methodology">Methodology</Link>
                <Link href="/blog">Blog</Link>
                <Link href="/docs">Docs</Link>
                <Link href="/pricing">Certification Pricing</Link>
                <Link href="/apply">Get Started</Link>
              </div>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Resources</h3>
              <div className="flex flex-col gap-1">
                <a href={`${REPO_URL}/blob/main/docs/QUICK_START.md`} target="_blank" rel="noopener noreferrer">Quick Start Guide</a>
                <a href={`${REPO_URL}/blob/main/docs/BENCHMARK_SPEC_V4.md`} target="_blank" rel="noopener noreferrer">Benchmark Spec v4 (GitHub)</a>
                <a href={`${REPO_URL}/blob/main/docs/LEADERBOARD_RULES_V1.md`} target="_blank" rel="noopener noreferrer">Leaderboard Rules</a>
                <a href={`${REPO_URL}/blob/main/CITATION.cff`} target="_blank" rel="noopener noreferrer">Citation (CITATION.cff)</a>
                <a href={REPO_URL} target="_blank" rel="noopener noreferrer">GitHub Repository</a>
              </div>
            </div>
            <div className="space-y-2">
              <h3 className="font-semibold text-foreground">Company</h3>
              <div className="flex flex-col gap-1">
                <Link href="/about">About QEncode</Link>
                <a href="mailto:support@qencode-benchmark.org">support@qencode-benchmark.org</a>
                <span>&copy; 2026 QEncode. Suite v4.</span>
              </div>
              <div className="pt-3">
                <Image src="/logo.png" alt="QEncode Benchmark" width={72} height={72} className="opacity-50" />
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

