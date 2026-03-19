import "./globals.css";
import Navbar from "@/components/Navbar";
import Link from "next/link";

export const metadata = {
  title: "QEncode Leaderboard",
  description: "Scientific benchmark leaderboard for QEncode Suite v1."
};

export default function RootLayout({ children }) {
  const REPO_URL = "https://github.com/jlabanimation-del/qencode-benchmark-suite";
  return (
    <html lang="en">
      <body>
        <Navbar />
        {children}
        <footer className="border-t mt-16">
          <div className="container py-8 text-sm text-muted-foreground flex flex-wrap items-center justify-between gap-3">
            <p>QEncode Benchmark Suite - reproducible quantum algorithm benchmarking.</p>
            <div className="flex items-center gap-4">
              <Link href="/leaderboard">Leaderboard</Link>
              <Link href="/benchmark">Benchmark</Link>
              <Link href="/docs">Docs</Link>
              <a href={REPO_URL} target="_blank" rel="noopener noreferrer">GitHub</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

