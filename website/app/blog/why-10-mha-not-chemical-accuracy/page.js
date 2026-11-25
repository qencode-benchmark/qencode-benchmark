import Link from "next/link";

const SLUG = "why-10-mha-not-chemical-accuracy";
const TITLE = "Why We Certify at 10 mHa, and What Our Results Below 1.6 mHa Really Show";
const DESCRIPTION =
  "28 of our 54 entries land below chemical accuracy (1.6 mHa). For most of them that says more about the molecule than the method: Hartree–Fock already starts within 2.7 mHa. Here is the one result that earns it, why the hard molecules stop just under 10 mHa, and why the bar is 10 mHa.";

export const metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: `/blog/${SLUG}` },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: `https://www.qencode-benchmark.org/blog/${SLUG}`,
    type: "article",
  },
};

const EASY = [
  ["H₂", "2.66", "< 0.001"],
  ["NH₃", "2.16", "0.032"],
  ["BeH₂", "1.98", "< 0.001"],
  ["H₂O", "0.54", "< 0.001"],
  ["water dimer", "0.18", "0.002"],
  ["LiH", "0.13", "0.003"],
  ["HF", "0.07", "< 0.001"],
];

const HARD = [
  ["H₄", "19.74", "2.22", "88.7"],
  ["C₄H₆", "22.51", "2.83", "87.4"],
  ["C₄H₄", "20.60", "3.83", "81.4"],
  ["N₂", "135.74", "4.40", "96.8"],
  ["benzene", "65.32", "8.74", "86.6"],
  ["H₆", "81.36", "9.27", "88.6"],
  ["H₈", "109.02", "9.80", "91.0"],
  ["H₁₀", "136.82", "9.98", "92.7"],
];

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-11-25">November 25, 2026</time>
          <span>·</span>
          <span>7 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">{TITLE}</h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          28 of our 54 published entries, covering 8 of the 16 molecules, land below chemical
          accuracy. It would be easy to write &ldquo;QEncode reaches chemical accuracy&rdquo; on the
          home page. We are not going to, and this post explains why, and what those results do
          and do not show.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <h2 className="text-xl font-semibold mt-2 mb-3">Two numbers on the leaderboard</h2>

        <p>
          Every entry is scored by its <strong>gap</strong>: how far the VQE energy lies above the
          exact ground-state energy of the same problem (CASCI, the exact answer within the chosen
          basis set and active space). Two lines matter:
        </p>

        <ul className="list-disc pl-6 space-y-1">
          <li>
            <strong>1.6 mHa</strong>, chemical accuracy: 1 kcal/mol = 1.594 mHa, the error at which
            computed reaction energies become useful for real chemistry.
          </li>
          <li>
            <strong>10 mHa</strong>, our certification bar: an entry is certified when its gap is
            below it.
          </li>
        </ul>

        <p>
          One caveat before anything else. Our gap is measured against the exact answer
          <em> of the model problem</em>, not against experiment. A gap under 1.6 mHa means the
          algorithm solved the model problem to chemical accuracy. Whether the model problem
          (a cc-pVDZ basis and a small active space) describes the real molecule to chemical
          accuracy is a separate question that the benchmark does not answer.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Most of the results below 1.6 mHa are easy cases</h2>

        <p>
          The fair way to judge a gap is to ask where the calculation started. VQE starts from the
          Hartree–Fock (HF) state, and for seven of the eight molecules below 1.6 mHa, HF is
          already within 2.7 mHa of the exact answer:
        </p>

        <div className="rounded-lg border overflow-hidden my-4 not-prose">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Molecule</th>
                <th className="text-right px-4 py-2.5 font-medium">HF starts at (mHa)</th>
                <th className="text-right px-4 py-2.5 font-medium">Best VQE gap (mHa)</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {EASY.map(([m, hf, best]) => (
                <tr key={m}>
                  <td className="px-4 py-2.5">{m}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{hf}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{best}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p>
          These results are correct and they reproduce. The algorithms really do close the
          remaining gap almost completely. But for HF, LiH, H₂O and the water dimer the starting
          point is already below 1.6 mHa, so landing below the line proves very little about the
          method. These molecules are in the suite to check that the pipeline is correct, not to
          show what quantum algorithms can do.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The one result that earns it</h2>

        <p>
          <strong>Formaldehyde (H₂CO)</strong> is different. HF starts 22.24 mHa above the exact
          answer, and ADAPT-VQE brings it down to <strong>1.12 mHa</strong>, recovering 94.9% of
          the correlation energy. That is a real chemical-accuracy result on a problem where HF is
          not good enough. Today it is the only one in the suite.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The hard molecules stop just under 10 mHa, by design</h2>

        <p>
          For the eight harder molecules, HF starts between 19.7 and 136.8 mHa away, and the best
          certified results land between 2.2 and 10 mHa:
        </p>

        <div className="rounded-lg border overflow-hidden my-4 not-prose">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Molecule</th>
                <th className="text-right px-4 py-2.5 font-medium">HF starts at (mHa)</th>
                <th className="text-right px-4 py-2.5 font-medium">Best gap (mHa)</th>
                <th className="text-right px-4 py-2.5 font-medium">Correlation recovered</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {HARD.map(([m, hf, best, pct]) => (
                <tr key={m}>
                  <td className="px-4 py-2.5">{m}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{hf}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{best}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p>
          Benzene, H₆, H₈ and H₁₀ all sit just under 10 mHa. That is not a coincidence. Our
          pipeline stops at the first attempt that certifies, and ADAPT-VQE stops adding operators
          once the gap drops below the bar. So these numbers show the methods <em>can reach
          10 mHa</em>. They do not show whether the methods could reach 1.6 mHa, because we never
          asked them to. For H₁₀ we know the limit is close: it certified with the last of the
          300 operators it was allowed.
        </p>

        <p>
          So the honest statement is: <strong>we have not shown chemical accuracy on any hard
          molecule</strong>. We have not shown it is out of reach either. One hint that it may be
          reachable: in an unpublished re-run, N₂ with UCCSD and a gradient-based optimiser reached
          0.049 mHa, against 10.83 mHa for the published gradient-free run (details in the
          repository, <code>docs/SUITE_BALANCE.md</code>).
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why the bar is 10 mHa</h2>

        <p>
          A certificate has to mean the same thing on anyone&rsquo;s computer. We regenerated every
          entry on a second machine with the same pinned software. Certification held for 44 of
          the 47 certified entries, but some energies moved: up to 15.85 mHa in the worst case,
          and five certified entries moved by more than 1.6 mHa. With a 1.6 mHa bar, those
          entries would pass or fail depending on which processor ran them. A certificate that
          depends on the machine is not a certificate. The full measurement is in{" "}
          <code>docs/CROSS_MACHINE.md</code>, and entries that did not hold are flagged on the
          leaderboard.
        </p>

        <p>
          The second reason is coverage. With a 1.6 mHa bar, eight of the sixteen molecules
          (every hard one) would have no certified entry today, and the benchmark would only
          measure the easy half of the suite.
        </p>

        <p>
          So the two lines answer different questions. <strong>10 mHa</strong> asks: does this
          method reproducibly get close to the exact answer? <strong>1.6 mHa</strong> asks: is the
          answer good enough for chemistry? Our certificate answers the first question only.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">How to read a result below 1.6 mHa</h2>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Check where HF starts.</strong> A small gap on a molecule HF already describes
            well is a correctness check, not a demonstration.
          </li>
          <li>
            <strong>Check the share of the correlation energy recovered.</strong> H₂CO at 1.12 mHa
            and 94.9% is a stronger result than LiH at 0.003 mHa from a 0.13 mHa start.
          </li>
          <li>
            <strong>Remember the reference.</strong> The gap is measured against the exact answer
            of the model problem, not against experiment.
          </li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-3">What comes next</h2>

        <p>
          We want the next chemical-accuracy claim to be one we can stand behind. The plan is to
          show both numbers on each entry page (where HF starts and how much of the correlation
          energy was recovered), and to rerun the hard molecules without stopping at 10 mHa, to
          find out which of them really reach 1.6 mHa, and whether those results hold across
          machines. When we have that, we will publish it here, including the molecules where it
          does not work.
        </p>

        <p>
          Every number in this post comes from the 54 published entries in the repository and can
          be checked with the open-source verifier.{" "}
          <Link href="/leaderboard" className="text-primary hover:underline">
            See the leaderboard
          </Link>
          .
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
