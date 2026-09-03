import Link from "next/link";

export const metadata = {
  title: "We Said Every Result Was Reproducible. Then We Tried to Check.",
  description:
    "Our verifier could not re-run 29 of our 54 published entries, and nobody had noticed — because a verifier that errors out looks like a broken command, not a broken guarantee. Fixing it revealed something harder: an entry certified close to the threshold is not robustly certified.",
  alternates: { canonical: "/blog/verifying-the-whole-database" },
  openGraph: {
    title: "We Said Every Result Was Reproducible. Then We Tried to Check.",
    description:
      "Three bugs in the tool that checks our claims, none in the results themselves — and a finding that generalises to any benchmark with a hard pass/fail threshold.",
    url: "https://www.qencode-benchmark.org/blog/verifying-the-whole-database",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "We Said Every Result Was Reproducible. Then We Tried to Check.",
  description:
    "QEncode's central claim is that any published benchmark entry can be independently rebuilt. Running that check across the whole database for the first time found three faults in the verifier — one of which made 29 of 54 entries impossible to verify at all — and a deeper result: entries certified close to the pass threshold do not survive being re-run on a different machine.",
  datePublished: "2026-09-03",
  dateModified: "2026-09-03",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/verifying-the-whole-database",
  keywords: [
    "reproducibility", "benchmark verification", "VQE", "quantum chemistry benchmark",
    "certification threshold", "COBYLA", "gradient-free optimization",
    "continuous integration", "scientific software", "QEncode",
  ],
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What does it mean for a VQE benchmark result to be reproducible?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "It means three things of decreasing strength. First, the procedure is identical and fully declared: same ansatz, optimiser, iteration budget, seed, active space and mapping, all recorded in the entry. Second, the outcome still satisfies the certification criterion when re-run, meaning the regenerated error is still below the threshold. Third, the energy matches bit for bit. Only the third is a strict determinism claim, and it holds only on a reference pinned environment. Across different machines, gradient-free optimisers such as COBYLA are not expected to produce bit-identical energies, because they choose each step by comparing two nearly equal numbers and a last-bit difference can send the run to a different local minimum.",
      },
    },
    {
      "@type": "Question",
      name: "Why can two machines get different answers from the same VQE calculation?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Because gradient-free optimisers amplify tiny arithmetic differences. A gradient-free optimiser picks its next step by comparing two nearly equal energies, so a difference in the thirteenth decimal place can flip a comparison, change the step, and land the run in a different local minimum. Two simulator backends that agree to 1e-13 Hartree on a single energy evaluation have ended 11 millihartree apart after running COBYLA. A different machine, with a different BLAS build or library version, is a larger perturbation than that. Gradient-based optimisers are effectively immune, because a 1e-13 perturbation moves a computed search direction by 1e-13 rather than flipping a decision.",
      },
    },
    {
      "@type": "Question",
      name: "What is a certification margin in a benchmark?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The distance between a result and the pass threshold. If a benchmark certifies results with an error below 10 millihartree, then an entry at 9.6 and an entry at 0.001 are both certified, but only the second has room to spare. The first can cross the line when re-run on a different machine. Measuring this on our own database, two entries certified at 6.1 and 9.6 millihartree regenerated at 20.5 and 19.0 on a different environment, while their headline status said only certified. Reporting the margin alongside the result makes the difference visible.",
      },
    },
    {
      "@type": "Question",
      name: "Why did nobody notice the benchmark verifier was broken?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Because a verifier that errors out looks like a broken command rather than a broken guarantee. Ours rejected 29 of 54 entries with an argument parsing error, which reads as a typo in how you invoked it, not as a failure of the reproducibility claim. Anyone checking a single entry would have assumed they had made a mistake. The fault only became visible when the tool was run across the entire database at once, which nobody had done. The lesson is that a checking tool needs to be exercised over everything it claims to check, automatically, not spot-checked by hand.",
      },
    },
  ],
};

function Stat({ value, label, tone }) {
  const color =
    tone === "bad" ? "text-destructive"
      : tone === "good" ? "text-primary"
      : "text-foreground";
  return (
    <div className="rounded-lg border p-4 text-center">
      <div className={`text-2xl font-semibold tabular-nums ${color}`}>{value}</div>
      <div className="text-xs text-muted-foreground mt-1 leading-5">{label}</div>
    </div>
  );
}

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-09-03">September 3, 2026</time>
          <span>·</span>
          <span>11 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          We Said Every Result Was Reproducible. Then We Tried to Check.
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          The whole point of this benchmark is that any published result can be rebuilt by
          someone else. We had a tool for exactly that. It turned out it could not run on
          more than half our own database, and nobody had noticed — because a verifier
          that errors out looks like a broken command, not a broken promise.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            We ran our own verifier across all 54 published entries for the first time.
            It found <strong>three bugs — all of them in the verifier, none in the
            results</strong>. After fixing them, all 54 reproduce. Then we put the check
            into CI, and CI failed, because we had asked for bit-identical energies across
            different machines and the numerics do not support that. Measuring what
            actually holds turned up the more interesting finding:{" "}
            <strong>an entry certified close to the threshold is not robustly
            certified</strong>.
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 not-prose">
          <Stat value="54/54" label="entries reproduce, after the fixes" tone="good" />
          <Stat value="29" label="entries the verifier could not run at all" tone="bad" />
          <Stat value="8.0 h" label="compute to check the database once" />
          <Stat value="2" label="entries that fail on another machine" tone="bad" />
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">A claim we had never tested</h2>

        <p>
          Every QEncode entry records everything needed to rebuild it: molecule, basis,
          active space, mapping, ansatz, optimiser, seed, iteration budget, package
          versions, and the commit that produced it.{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">verify_entry.py</code>{" "}
          re-runs an entry from that record and compares the energy. That tool is the whole
          reproducibility claim, made executable.
        </p>

        <p>
          We had run it on individual entries many times. We had never run it on all of
          them. So we did.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Bug one: it could not run 29 of 54 entries</h2>

        <p>
          Entries record the ansatz in the pipeline&rsquo;s internal vocabulary. The
          command line takes a different one. 29 entries store{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">ansatz_type: &quot;hea&quot;</code>;
          the flag accepts only{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">hardware_efficient</code>.
          Every one of those verifications died at the first call:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p>generate_entry_v4.py: error: argument --ansatz-type:</p>
          <p>{"    "}invalid choice: &apos;hea&apos; (choose from &apos;uccsd&apos;, &apos;hardware_efficient&apos;, &apos;adapt&apos;)</p>
        </div>

        <p>
          A sibling case, <code className="font-mono text-xs bg-muted px-1 rounded">uccsd_tapered</code>{" "}
          → <code className="font-mono text-xs bg-muted px-1 rounded">uccsd</code>, was already
          handled by a string replacement. <code className="font-mono text-xs bg-muted px-1 rounded">hea</code>{" "}
          was simply never mapped.
        </p>

        <div className="rounded-lg border-l-4 border-destructive bg-destructive/5 p-5 not-prose">
          <p className="text-sm text-foreground leading-6">
            <strong>This is why the claim had never been tested.</strong> More than half
            the database could not be checked, and the failure looked like a configuration
            error. Anyone verifying a single entry would reasonably have concluded they had
            typed something wrong. It only became visible by running the tool across
            everything at once — which nobody had done.
          </p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">Bug two: three entries re-ran at the wrong budget</h2>

        <p>
          With that fixed, three entries still failed, by up to 221 mHa. The cause split
          the database perfectly on a single field:
        </p>

        <div className="rounded-md border not-prose overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/60">
              <tr className="text-left">
                <th className="px-3 py-2 font-semibold">recorded <code>max_iterations</code></th>
                <th className="px-3 py-2 font-semibold text-right">entries</th>
                <th className="px-3 py-2 font-semibold text-right">reproduced</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr className="border-t">
                <td className="px-3 py-2"><strong>500</strong> (the default)</td>
                <td className="px-3 py-2 text-right">51</td>
                <td className="px-3 py-2 text-right font-semibold">51 — 100%</td>
              </tr>
              <tr className="border-t bg-destructive/5">
                <td className="px-3 py-2">1000</td>
                <td className="px-3 py-2 text-right">2</td>
                <td className="px-3 py-2 text-right font-semibold">0</td>
              </tr>
              <tr className="border-t bg-destructive/5">
                <td className="px-3 py-2">10000</td>
                <td className="px-3 py-2 text-right">1</td>
                <td className="px-3 py-2 text-right font-semibold">0</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p>
          The verifier never passed the recorded iteration cap. Entries needing more than
          500 iterations were silently re-run at 500 and landed somewhere else. One line.
          All three then reproduced — the worst of them, N₂, in 2.1 hours.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Bug three: it only worked on our machine</h2>

        <p>
          The pipeline refuses to <em>write</em> an entry from a dirty git tree or a drifted
          package set. That is correct. But the verifier had no way to override it, so
          verification was impossible for anyone whose environment was not byte-identical
          to ours — which is everyone checking our work from outside, and the only audience
          the tool has.
        </p>

        <p>
          Three bugs. All three in the checking. <strong>None in the results.</strong>{" "}
          After the fixes, all 54 entries reproduce — including H₁₀ at 20 qubits, which
          took two hours, and H₆, which took 2.1. Eight hours of compute to check the
          database once.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Then we put it in CI, and CI failed</h2>

        <p>
          A check nobody runs is not a check, so we added it to continuous integration:
          a six-entry subset on every push, the rest weekly. The first weekly run failed
          every shard.
        </p>

        <p>
          Not a new bug. We had asked CI to confirm that a regenerated energy matched the
          published one to 10⁻⁶ Ha, on a different machine. The numerics do not support
          that, and{" "}
          <Link href="/blog/vqe-reproducibility-threading-bug" className="text-primary hover:underline">
            we already knew why
          </Link>.
        </p>

        <p>
          A gradient-free optimiser like COBYLA picks its next step by <em>comparing</em>{" "}
          two nearly equal energies. A difference in the thirteenth decimal can flip that
          comparison, change the step, and land the run in a different local minimum. We
          had measured exactly this between two simulator backends on the same machine:
          agreement to 2.6 × 10⁻¹³ Ha on a single energy evaluation, and{" "}
          <strong>11 mHa apart</strong> after COBYLA. A different machine is a bigger
          perturbation than a different backend.
        </p>

        <p>So we measured what actually holds. Re-running 40 entries on a drifted environment:</p>

        <div className="rounded-md border not-prose overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/60">
              <tr className="text-left">
                <th className="px-3 py-2 font-semibold">energy movement</th>
                <th className="px-3 py-2 font-semibold text-right"></th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr className="border-t"><td className="px-3 py-2">median</td><td className="px-3 py-2 text-right">6.7 × 10⁻⁸ Ha</td></tr>
              <tr className="border-t"><td className="px-3 py-2">90th percentile</td><td className="px-3 py-2 text-right">2.1 × 10⁻³ Ha</td></tr>
              <tr className="border-t"><td className="px-3 py-2">maximum</td><td className="px-3 py-2 text-right font-semibold">1.4 × 10⁻² Ha</td></tr>
            </tbody>
          </table>
        </div>

        <p>
          <strong>17 of 40 exceeded the strict tolerance while still being perfectly
          valid results.</strong> That gap — between &ldquo;the energy is identical&rdquo;
          and &ldquo;the entry is still correct&rdquo; — is the whole point. Only the
          second is a property that travels between machines.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What reproducible has to mean</h2>

        <p>
          We wrote the definition down rather than letting CI imply a stronger one than the
          data support. Three claims, in decreasing strength:
        </p>

        <ol className="list-decimal pl-6 space-y-2">
          <li>
            <strong>The procedure is identical and fully declared.</strong> Same ansatz,
            optimiser, iteration budget, seed, active space, mapping. All recorded.
          </li>
          <li>
            <strong>The outcome still satisfies the certification criterion.</strong> The
            regenerated error is still under the threshold. This is what should hold on any
            machine.
          </li>
          <li>
            <strong>The energy matches bit for bit.</strong> Claimed only on the reference
            pinned environment.
          </li>
        </ol>

        <p>
          Anything stronger than (2) across machines is aspirational, and currently false
          for COBYLA-style methods. CI now checks (2). The pinned reference environment
          checks (3).
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The finding that outlasts the bugs</h2>

        <p>
          With CI asking the right question, two entries still failed. Not a bug — a
          property of those entries:
        </p>

        <div className="rounded-md border not-prose overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/60">
              <tr className="text-left">
                <th className="px-3 py-2 font-semibold">entry</th>
                <th className="px-3 py-2 font-semibold text-right">published error</th>
                <th className="px-3 py-2 font-semibold text-right">re-run elsewhere</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr className="border-t">
                <td className="px-3 py-2">C₄H₄ (parity / HEA)</td>
                <td className="px-3 py-2 text-right">6.1 mHa</td>
                <td className="px-3 py-2 text-right font-semibold text-destructive">20.5 mHa</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2">C₄H₄ (JW / HEA)</td>
                <td className="px-3 py-2 text-right">9.6 mHa</td>
                <td className="px-3 py-2 text-right font-semibold text-destructive">19.0 mHa</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p className="text-sm text-muted-foreground">
          The certification threshold is 10 mHa. Both were certified. Both stop being
          certified when rebuilt somewhere else.
        </p>

        <p>
          <strong>An entry certified close to the threshold is not robustly
          certified.</strong> Our leaderboard had been showing an entry at 9.6 mHa and one
          at 0.001 mHa identically — both simply &ldquo;certified&rdquo;. They are not the
          same thing. One survives being re-run elsewhere and one does not.
        </p>

        <p>
          So we added a <strong>certification margin</strong>: the distance from the
          threshold, reported per entry. Ten of our 47 certified entries sit within 20% of
          the line. The tightest is H₁₀, certified at 9.977 mHa against a 10 mHa
          threshold — a margin of <strong>0.2%</strong>.
        </p>

        <p>
          The two fragile entries are flagged, not withdrawn. They reproduce exactly on the
          reference environment, which is what certification attests. What changed is that
          the fragility is now visible instead of implied.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">A trap worth passing on</h2>

        <p>
          Midway through, we tried to predict which entries would fail by arithmetic:
          published error plus measured energy movement, compared to the threshold. It
          named four. We tested them. <strong>Two passed</strong> — their energy had moved{" "}
          <em>toward</em> the reference, so the error <em>shrank</em>: 9.283 → 8.405 mHa,
          and 7.917 → 5.684 mHa.
        </p>

        <p>
          The movement is unsigned; it does not tell you the direction. Had we trusted the
          arithmetic we would have branded two healthy entries as fragile. Fragility gets
          established by running the check, never by inferring it.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What generalises</h2>

        <p>
          Little of this is specific to quantum chemistry.
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>A broken checker looks like a broken command.</strong> Failures that
            surface as usage errors get attributed to the user, not to the tool. Ours hid
            in plain sight for months.
          </li>
          <li>
            <strong>Run the checker over everything, automatically.</strong> Spot-checking
            found nothing across many individual runs. One exhaustive pass found three
            bugs in an afternoon.
          </li>
          <li>
            <strong>Any benchmark with a hard threshold has entries just inside it</strong>{" "}
            whose status depends on the environment. If you publish a pass/fail label
            without a margin, you are hiding that.
          </li>
          <li>
            <strong>State the guarantee you can defend.</strong> It is tempting to let
            &ldquo;reproducible&rdquo; imply bit-identity. We measured what our own methods
            actually deliver and wrote that down instead.
          </li>
        </ul>

        <p>
          All 54 entries, the sweep records, the measured envelopes and the tools are in{" "}
          <Link href="https://github.com/qencode-benchmark/qencode-benchmark" className="text-primary hover:underline">
            the repository
          </Link>
          , including the runs that failed and the two entries that still do.
        </p>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm text-muted-foreground leading-6">
            QEncode is an open benchmark for reproducible VQE quantum chemistry. Every
            entry records its full provenance so results can be independently rebuilt —
            and, as of this month, so that claim is checked on every commit. See the{" "}
            <Link href="/leaderboard" className="text-primary hover:underline">leaderboard</Link>{" "}
            or{" "}
            <Link href="/leaderboard/guide" className="text-primary hover:underline">
              what the numbers mean
            </Link>.
          </p>
        </div>
      </div>
    </main>
  );
}
