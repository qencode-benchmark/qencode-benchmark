import Link from "next/link";

export const metadata = {
  title: "Chemical Accuracy vs. Certification: What the Gap Bars on the Leaderboard Mean",
  description:
    "The leaderboard shows two thresholds: a 1.6 mHa chemical accuracy line and a 10 mHa certification threshold. Here's why they're different, what the colored bars measure, and how to read H₂O's red bars alongside H₂'s green ones.",
  alternates: { canonical: "/blog/chemical-accuracy-vs-certification" },
  openGraph: {
    title: "Chemical Accuracy vs. Certification: What the Gap Bars Mean",
    description:
      "Why H₂ shows green bars and H₂O shows red — and why both are correct. A guide to reading the QEncode leaderboard accuracy scale.",
    url: "https://www.qencode-benchmark.org/blog/chemical-accuracy-vs-certification",
    type: "article",
  },
};

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-05-07">May 7, 2026</time>
          <span>·</span>
          <span>6 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          Chemical Accuracy vs. Certification: What the Gap Bars on the Leaderboard Mean
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          When you open the leaderboard and filter to H₂O, all the bars are red. Filter to H₂ and
          they're all green. Both are correct. Here's why — and what the two accuracy thresholds
          actually mean.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <h2 className="text-xl font-semibold mt-2 mb-3">The error metric: |E_VQE − E_FCI|</h2>

        <p>
          Every entry on the leaderboard is evaluated by a single number: the absolute difference
          between the VQE ground-state energy and the exact Full Configuration Interaction (FCI)
          energy within the same active space. We call this the <strong>gap</strong>:
        </p>

        <div className="rounded-lg bg-muted/40 border px-5 py-4 my-4 font-mono text-sm text-center">
          gap = |E<sub>VQE</sub> − E<sub>FCI</sub>|
        </div>

        <p>
          This metric has a physical meaning: it tells you how much energy the VQE ansatz
          fails to recover compared to the best possible wavefunction within the chosen orbital
          space. A gap of zero means the ansatz found the exact ground state. A gap of 3.5 mHa
          means it's 3.5 milliHartree above the exact solution.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Chemical accuracy: 1.6 mHa</h2>

        <p>
          The gold standard in computational chemistry is <strong>chemical accuracy</strong>:
          an error small enough that the computed thermochemistry (reaction energies, activation
          barriers, bond dissociation energies) matches experiment to within 1 kcal/mol. In
          Hartree units, 1 kcal/mol = 1.594 mHa ≈ <strong>1.6 mHa</strong>.
        </p>

        <p>
          Below this threshold, a computed energy difference is reliable enough to inform
          real chemical decisions — predicting which reaction pathway is preferred, whether a
          transition state is accessible at room temperature, or how stable a molecular complex is.
          Above it, you're in the regime of "qualitatively correct but not quantitatively
          reliable."
        </p>

        <p>
          Chemical accuracy is the aspirational target. It's what separates a
          scientifically useful energy estimate from a demonstration that the algorithm ran.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The certification threshold: 10 mHa</h2>

        <p>
          QEncode's certification threshold is set at <strong>10 mHa (0.01 Ha)</strong> — about
          6× looser than chemical accuracy. Why not use 1.6 mHa directly?
        </p>

        <p>
          Two reasons. First, many interesting quantum algorithm demonstrations don't yet reach
          chemical accuracy, especially on 8-qubit molecules with standard UCCSD reps=1. Setting
          the bar at 1.6 mHa would exclude a large fraction of valid, reproducible, scientifically
          interesting results. Second, the certification threshold is about <em>reproducibility</em>,
          not optimality — it confirms the implementation is correct and the result is consistent
          across runs, not that the algorithm is the best possible.
        </p>

        <p>
          Think of it this way: certification asks "did this run correctly and consistently?"
          Chemical accuracy asks "is this result good enough to trust for chemistry?" These are
          different questions.
        </p>

        <div className="rounded-lg border bg-muted/20 px-5 py-4 my-6 space-y-2">
          <div className="flex items-baseline gap-3">
            <span className="w-3 h-3 rounded-full bg-green-500 inline-block shrink-0 mt-1" />
            <div>
              <span className="font-medium">Gap &lt; 1.6 mHa</span>
              <span className="text-muted-foreground"> — chemical accuracy (excellent)</span>
            </div>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="w-3 h-3 rounded-full bg-amber-400 inline-block shrink-0 mt-1" />
            <div>
              <span className="font-medium">1.6 mHa – 10 mHa</span>
              <span className="text-muted-foreground"> — certified but not chemically accurate</span>
            </div>
          </div>
          <div className="flex items-baseline gap-3">
            <span className="w-3 h-3 rounded-full bg-red-400 inline-block shrink-0 mt-1" />
            <div>
              <span className="font-medium">Gap &gt; 10 mHa</span>
              <span className="text-muted-foreground"> — not certified (excluded from main leaderboard)</span>
            </div>
          </div>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why H₂ is green and H₂O is red</h2>

        <p>
          The colored bars on the leaderboard show where each entry sits on a log scale
          relative to the best and worst gap in the currently visible set. Green = best (lowest
          gap), red = worst (highest gap) within what you're looking at.
        </p>

        <p>
          H₂ under Jordan-Wigner UCCSD achieves a gap of <strong>1.15 × 10⁻⁹ Ha</strong> — about
          one nanoHartree. That's essentially machine precision; the VQE found the exact ground
          state of the [2,2] active space to within floating-point noise. H₂ is a trivially easy
          problem for UCCSD: the [2,2] space has only a single double excitation, so UCCSD with
          one repetition is the exact solver.
        </p>

        <p>
          H₂O UCCSD achieves <strong>3.54 × 10⁻³ Ha</strong>. That's about 3 million times larger
          than H₂'s gap. On the log scale the bars use, H₂O sits near the top (red) and H₂ sits
          near the bottom (green), even though both are certified and both represent correct,
          reproducible results.
        </p>

        <p>
          The bars are not saying H₂O is broken. They're saying H₂O is a harder problem. The
          [4,4] active space has many more excitation amplitudes, a higher-dimensional optimization
          landscape, and UCCSD reps=1 is not the exact solver for it the way it is for H₂.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Reading the bars when filtering by molecule</h2>

        <p>
          When you filter the leaderboard to a single molecule — say, H₂O — the bar scale
          automatically adjusts to the min and max gap within that filtered set. This means:
        </p>

        <ul className="list-disc pl-6 space-y-1">
          <li>
            The best H₂O entry (JW UCCSD, 3.54 mHa) shows as <span className="text-green-600 font-medium">green</span>
          </li>
          <li>
            The worst certified H₂O entry (JW HEA, 7.45 mHa) shows as <span className="text-red-500 font-medium">red</span>
          </li>
          <li>
            The bars let you compare relative performance within H₂O, not against H₂
          </li>
        </ul>

        <p>
          Switch to "All molecules" and the scale becomes global: now H₂ at 1 nHa is green and
          H₂O at 3.5 mHa is red, because the scale spans the full range of gaps in the dataset.
          Both views are correct — they just answer different questions.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The research tier: beyond certification</h2>

        <p>
          Some molecules are genuinely too hard for UCCSD reps=1 to certify at any encoding.
          N₂ with a [6,6] active space is a prime example: the best UCCSD gap we achieve is
          44 mHa — 4× above the certification threshold. This isn't a convergence failure;
          it's a property of N₂'s triple bond, which creates strong multi-reference correlation
          that single-reference UCCSD cannot capture.
        </p>

        <p>
          These entries appear in the <strong>Research tab</strong> on the leaderboard — separate
          from the certified results, with a note explaining the physical reason for the large gap.
          The data is correct and reproducible; the method just has a known limitation for this
          class of molecule.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Summary</h2>

        <div className="rounded-lg border overflow-hidden my-4">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Molecule</th>
                <th className="text-right px-4 py-2.5 font-medium">Best gap</th>
                <th className="text-left px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y text-sm">
              <tr>
                <td className="px-4 py-2.5">H₂, HF, LiH</td>
                <td className="px-4 py-2.5 text-right font-mono">&lt; 10 nHa</td>
                <td className="px-4 py-2.5 text-green-600">Chemical accuracy ✓</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5">BeH₂, H₂O</td>
                <td className="px-4 py-2.5 text-right font-mono">~3.5 mHa</td>
                <td className="px-4 py-2.5 text-amber-600">Certified, above chemical accuracy</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5">N₂ [6,6]</td>
                <td className="px-4 py-2.5 text-right font-mono">44 mHa</td>
                <td className="px-4 py-2.5 text-red-500">Research tier (UCCSD limitation)</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p>
          The leaderboard is designed to show all of this honestly. Certified entries that don't
          reach chemical accuracy are included — they represent real progress. The gap bars let
          you see at a glance where each result sits, both within a molecule and across the full
          suite.{" "}
          <Link href="/leaderboard" className="text-primary hover:underline">
            Explore the leaderboard
          </Link>{" "}
          to see the full picture.
        </p>

      </div>

      <div className="mt-12 pt-8 border-t flex items-center justify-between">
        <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← All posts
        </Link>
        <Link href="/leaderboard" className="text-sm font-medium text-primary hover:underline">
          View leaderboard →
        </Link>
      </div>
    </main>
  );
}
