import { loadLeaderboardData } from "@/lib/data";
import LeaderboardClient from "./LeaderboardClient";
import Link from "next/link";
import { Button } from "@/components/ui/button";

// Always server-render at request time — never prerender at build.
// This avoids build failures when the DB is empty and allows live updates.
export const dynamic = "force-dynamic";

export const metadata = {
  title: "Quantum Algorithm Leaderboard",
  description:
    "Compare certified quantum algorithm benchmark results by molecule, accuracy gap, circuit depth, and two-qubit gate cost on the QEncode leaderboard.",
  keywords: [
    "quantum algorithm leaderboard",
    "VQE leaderboard",
    "quantum benchmark rankings",
    "circuit depth and gate count"
  ],
  alternates: {
    canonical: "/leaderboard"
  },
  openGraph: {
    title: "QEncode Leaderboard - Certified Quantum Benchmark Rankings",
    description:
      "Explore public certified rankings for quantum chemistry benchmarks across accuracy and hardware cost.",
    url: "/leaderboard"
  }
};

export default async function LeaderboardPage() {
  const { acc, cost, balanced, metadata } = await loadLeaderboardData();
  const suiteLabel = String(metadata.suite_version || "").replace(/^v/i, "");
  const rulesLabel = String(metadata.leaderboard_rules || "").replace(/^v/i, "");

  return (
    <div className="container py-16">
      <h1 className="text-3xl sm:text-4xl font-bold mb-2">Leaderboard</h1>
      <p className="text-muted-foreground mb-8 max-w-xl">
        Public rankings include only certified entries with official trust filtering ({metadata.generation_date}).
      </p>
      <p className="text-xs text-muted-foreground -mt-6 mb-6 max-w-2xl">
        Entry counts can differ by molecule when some configurations are not yet certified.
      </p>
      <div className="flex flex-wrap gap-2 mb-6">
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Suite v{suiteLabel}
        </span>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Rules v{rulesLabel}
        </span>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Trust: {metadata.trust_filter}
        </span>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Entries: {metadata.entries_included}
        </span>
      </div>
      <div className="mb-8 rounded-lg border p-4 bg-muted/30 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          Need your results listed here? Purchase certification and apply for managed execution access.
        </p>
        <div className="flex gap-2">
          <Button asChild size="sm"><Link href="/pricing">Pricing</Link></Button>
          <Button asChild size="sm" variant="outline"><Link href="/apply">Apply for Access</Link></Button>
        </div>
      </div>
      <LeaderboardClient acc={acc} cost={cost} balanced={balanced} />
    </div>
  );
}

