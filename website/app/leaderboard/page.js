import { loadLeaderboardData } from "@/lib/data";
import LeaderboardClient from "./LeaderboardClient";

export default function LeaderboardPage() {
  const { acc, cost, balanced, metadata } = loadLeaderboardData();

  return (
    <div className="container py-16">
      <h1 className="text-3xl sm:text-4xl font-bold mb-2">Leaderboard</h1>
      <p className="text-muted-foreground mb-8 max-w-xl">
        Rankings across molecules, encodings, and ansatz types. Certified-only dataset ({metadata.generation_date}).
      </p>
      <div className="flex flex-wrap gap-2 mb-6">
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Suite v{metadata.suite_version}
        </span>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Rules v{metadata.leaderboard_rules}
        </span>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Trust: {metadata.trust_filter}
        </span>
        <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium">
          Entries: {metadata.entries_included}
        </span>
      </div>
      <LeaderboardClient acc={acc} cost={cost} balanced={balanced} />
    </div>
  );
}

