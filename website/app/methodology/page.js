export const metadata = {
  title: "Benchmark Methodology",
  description:
    "Understand QEncode benchmark methodology, leaderboard rules, scoring logic, and data provenance for certified quantum algorithm rankings.",
  keywords: [
    "quantum benchmark methodology",
    "leaderboard scoring rules",
    "quantum ranking criteria"
  ],
  alternates: {
    canonical: "/methodology"
  },
  openGraph: {
    title: "QEncode Methodology",
    description:
      "Fixed benchmark suite and transparent scoring framework for reproducible quantum leaderboard rankings.",
    url: "/methodology"
  }
};

export default function MethodologyPage() {
  return (
    <div>
      <h1>Methodology</h1>
      <p className="muted">
        This leaderboard follows a fixed benchmark suite, fixed algorithm constraints, certified-only eligibility,
        transparent scoring, and public dataset release.
      </p>

      <section className="card" style={{ marginTop: 12 }}>
        <h3>Rules Snapshot (v1)</h3>
        <ul>
          <li>Eligibility: suite match + trust_level = certified + required metrics</li>
          <li>Scope: rankings computed per molecule</li>
          <li>Accuracy: sort by lowest gap</li>
          <li>Hardware cost: sort by lowest two-qubit gates</li>
          <li>Balanced score: gap × depth (lower is better)</li>
        </ul>
      </section>

      <section className="card" style={{ marginTop: 12 }}>
        <h3>Data Provenance</h3>
        <p>
          Generated from the release dataset and metadata committed in this project under
          <code> datasets/qencode_leaderboard_v2/</code>.
        </p>
        <p className="muted">
          Canonical docs in repo: <code>docs/LEADERBOARD_RULES_V1.md</code> and
          <code> docs/BENCHMARK_SPECIFICATION_V1.md</code>.
        </p>
      </section>
    </div>
  );
}

