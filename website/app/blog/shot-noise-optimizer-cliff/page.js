import Link from "next/link";

export const metadata = {
  title: "We Tested Three VQE Optimizers Under Shot Noise. Two of Our Own Explanations Died.",
  description:
    "780 seeded VQE runs across 8 molecules. COBYLA's viability depends entirely on shot budget. Adam is consistently robust. L-BFGS-B swings from 9 to 700 mHa with nothing about the Hamiltonian predicting which. Includes a correction to an earlier version of this post.",
  alternates: { canonical: "/blog/shot-noise-optimizer-cliff" },
  openGraph: {
    title: "We Tested Three VQE Optimizers Under Shot Noise. Two of Our Own Explanations Died.",
    description:
      "780 runs, 8 molecules. You cannot predict from a Hamiltonian whether a quasi-Newton optimizer will survive your shot budget. You have to measure it.",
    url: "https://www.qencode-benchmark.org/blog/shot-noise-optimizer-cliff",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "We Tested Three VQE Optimizers Under Shot Noise. Two of Our Own Explanations Died.",
  description:
    "780 seeded VQE runs across 8 molecules measuring how COBYLA, L-BFGS-B and Adam degrade under finite sampling, including a correction to an earlier claim that the shot budget scales with Hamiltonian size.",
  datePublished: "2026-08-25",
  dateModified: "2026-08-25",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/shot-noise-optimizer-cliff",
  keywords: [
    "VQE shot noise", "COBYLA", "L-BFGS-B", "Adam optimizer", "SPSA",
    "parameter-shift gradients", "finite sampling", "quantum chemistry benchmark",
    "optimizer comparison", "reproducibility", "QEncode",
  ],
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Which VQE optimizer is most robust to shot noise?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Across 8 molecules at 1,000 shots per energy evaluation, Adam was the only optimizer that never failed catastrophically on a molecule its ansatz could actually fit, landing between 4.2 and 12.4 mHartree. L-BFGS-B ranged from 9.1 to 700.1 mHartree on the same four molecules, and no property of the Hamiltonian we examined predicted which outcome you would get. COBYLA was usable at 10,000 shots on small systems but collapsed to between 64 and 1093 mHartree at 1,000. Note that we did not test SPSA, which much of the literature recommends specifically for this regime.",
      },
    },
    {
      "@type": "Question",
      name: "Does the shot budget a VQE optimizer needs scale with Hamiltonian size?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No. We initially claimed it did, based on two molecules, and extending to eight falsified it. BeH2 has the smallest Hamiltonian we tested at 20 Pauli terms and a perfect noiseless baseline, yet L-BFGS-B reached only 58.9 mHartree at 1,000 shots, six times worse than water at 62 terms. LiH, with an excellent baseline and 155 terms, collapsed to 700 mHartree. Neither term count nor how well the ansatz fits the molecule predicted the outcome.",
      },
    },
    {
      "@type": "Question",
      name: "Why do published VQE optimizer comparisons disagree with each other?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Largely because the shot budget and the noise model differ between studies and are often not foregrounded. Our own data shows COBYLA reaching 7.8 mHartree on BeH2 at 10,000 shots and 64.4 mHartree at 1,000 on the same molecule, so a study at one budget can reasonably call it usable while a study at another calls it broken. Gate noise and sampling noise also perturb the objective differently: gate noise biases a smooth surface, which a trust-region method tolerates, while sampling makes the surface stochastic, which it does not.",
      },
    },
    {
      "@type": "Question",
      name: "Can a noiseless VQE benchmark predict hardware performance?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No, and it is not meant to. Certified QEncode entries reach accuracies far below what finite sampling can resolve at realistic budgets: one LiH entry certifies at 0.096 mHartree while the sampling spread on that circuit at 100,000 shots is roughly 2.5 mHartree, about 26 times larger. Separating algorithmic accuracy from sampling is the point of a noiseless suite, but a certified gap is a statement about an algorithm, not a prediction about a device.",
      },
    },
  ],
};

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <script type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }} />
      <script type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }} />
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-08-25">August 25, 2026</time>
          <span>·</span><span>10 min read</span><span>·</span><span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          We Tested Three VQE Optimizers Under Shot Noise. Two of Our Own Explanations Died.
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Every QEncode entry is computed with exact arithmetic. Real devices sample instead,
          so we measured what happens to three optimizers when the energy becomes noisy —
          780 runs across eight molecules, on the same Hamiltonians our published entries use.
          The measurements held. Two explanations we built on top of them did not.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-5 not-prose">
          <p className="text-sm font-semibold text-amber-900 dark:text-amber-200 mb-2">
            Correction — 25 August 2026
          </p>
          <p className="text-sm text-amber-900/90 dark:text-amber-200/90 leading-6">
            An earlier version of this post, published the same day from two molecules, claimed
            that <em>&ldquo;the shot budget a gradient optimizer needs scales with the size of the
            Hamiltonian.&rdquo;</em> Extending the study to eight molecules falsified that. BeH₂,
            the smallest Hamiltonian we tested, behaves worse than water at three times the size.
            The claim is withdrawn and the data that killed it is below.
          </p>
        </div>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            At 1,000 shots per energy evaluation, <strong>COBYLA</strong> lands between 64 and 1093
            mHartree — but is fine at 10,000 shots on small systems, so its reputation depends
            entirely on the budget a study chose. <strong>Adam</strong> never failed catastrophically
            on a molecule its ansatz could fit. <strong>L-BFGS-B</strong> swings from 9 to 700
            mHartree, and <strong>nothing we measured about the Hamiltonian predicts which you
            get</strong>. The practical conclusion is unglamorous: you cannot infer this from your
            problem. You have to test it.
          </p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">The setup</h2>

        <p>
          Each published QEncode entry stores its full Pauli decomposition, so we rebuilt the
          operators straight from the artifacts — the exact ground state of the reconstruction
          matches the stored value to <span className="font-mono text-xs">2.7e-15</span> Hartree.
          On each we ran a hardware-efficient ansatz from the Hartree-Fock determinant, then
          optimized with COBYLA, L-BFGS-B (parameter-shift gradients) and Adam, at exact
          evaluation, 10,000 shots and 1,000 shots, ten seeds each.
        </p>

        <p>
          Two disciplines mattered more than anything else. <strong>We calibrated at zero noise
          first</strong> — an early attempt had Adam at 292 mHartree against COBYLA&rsquo;s 0.73
          with no noise at all, which was an unequal iteration budget rather than a finding. And
          <strong> we seeded the sampling</strong>. Our first 180 runs left PennyLane&rsquo;s shot
          RNG unseeded, which made them irreproducible; we found this only because a reader asked
          whether the numbers could be regenerated. They could not. They can now.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">All eight molecules</h2>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            Median gap in mHa over 10 seeds — exact / 10,000 shots / 1,000 shots
          </p>
          <p>molecule  terms          Adam        L-BFGS-B          COBYLA</p>
          <p>BeH₂         20   0.0/3.3/12.4    0.0/2.0/58.9    0.1/7.8/64.4</p>
          <p>H₂O          62   0.3/1.2/ 6.8    0.4/4.4/ 9.1   0.4/48.7/1009.8</p>
          <p>NH₃         132   1.6/0.6/ 4.2    0.5/3.1/14.6  5.1/289.5/1093.3</p>
          <p>LiH         155   0.1/1.1/ 4.9   0.1/4.1/700.1 61.4/655.6/ 676.7</p>
          <p className="mt-2 text-muted-foreground"># below: ansatz fits poorly even at zero noise</p>
          <p>H₄          132  8.3/208.3/ 9.5   6.4/19.8/378.5 17.1/495.4/844.5</p>
          <p>C₄H₄        185  20.3/18.6/14.5 17.6/127.9/199.9 246.3/286.1/744.0</p>
          <p className="mt-2 text-muted-foreground"># below: our ansatz was too shallow — see limits</p>
          <p>N₂          378  842/831/813     743/918/1037    963/1116/1439</p>
          <p>benzene     914   66/142/186     201/367/421     743/849/1589</p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">Both of our explanations failed</h2>

        <p>
          <strong>First hypothesis: it scales with Hamiltonian size.</strong> Plausible — sampling
          error in an energy grows with the number of terms you are estimating. It survived two
          molecules and died on the third. BeH₂ has 20 terms and a perfect noiseless baseline, and
          L-BFGS-B still only reaches 58.9 mHartree at 1,000 shots, six times worse than water at
          62 terms. LiH, at 155 terms with an equally good baseline, collapses to 700.
        </p>

        <p>
          <strong>Second hypothesis: it tracks how well the ansatz fits.</strong> Also plausible,
          also dead. Ordered by noiseless baseline, the four clean molecules go BeH₂ (0.00), LiH
          (0.07), H₂O (0.34), NH₃ (0.49) — and their L-BFGS-B results at 1,000 shots go 58.9,
          700.1, 9.1, 14.6. No relationship.
        </p>

        <p>
          We designed a control specifically to test the first idea: NH₃ and H₄ have{" "}
          <em>identical</em> Hamiltonian sizes at 132 terms. L-BFGS-B reaches 14.6 mHartree on one
          and 378.5 on the other. Same size, 26× apart.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What actually survives</h2>

        <p>
          <strong>Adam is consistently robust.</strong> On the four molecules whose ansatz fits,
          it lands at 4.2, 4.9, 6.8 and 12.4 mHartree at 1,000 shots. Never a collapse. This is
          unsurprising — it is designed for stochastic gradients — but it is worth having measured
          rather than assumed.
        </p>

        <p>
          <strong>COBYLA&rsquo;s reputation is a shot-budget artifact.</strong> On BeH₂ it reaches
          7.8 mHartree at 10,000 shots and 64.4 at 1,000. On water, 48.7 and 1009.8. A study run at
          one budget can call it perfectly usable and a study at another can call it broken, and
          both are reporting honestly. That, more than anything, explains why published optimizer
          comparisons contradict each other.
        </p>

        <p>
          <strong>L-BFGS-B is unpredictable.</strong> Nine to seven hundred mHartree across four
          well-behaved molecules, with neither size, nor λ, nor baseline quality forecasting it.
          This is the finding we would most like to explain and cannot. The practical advice that
          follows is unglamorous but honest: <strong>if you are running a quasi-Newton optimizer
          at a finite shot budget, measure whether it survives on your problem. You cannot infer
          it.</strong>
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Where this sits in the literature</h2>

        <p>
          None of this is novel. Optimizer robustness under noise is well studied, and our results
          largely agree with it: gradient-based methods suffer because parameter-shift gradients
          are themselves sampled, and Adam and BFGS are both known to get stuck in local minima —
          which we saw repeatedly as reproducible trap basins.
        </p>

        <p>
          One omission we should name. Much of that literature recommends{" "}
          <strong>SPSA</strong> for precisely this regime, and we did not test it. Comparing three
          optimizers while leaving out the one the field recommends for noisy objectives is a real
          gap, and the obvious next step.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What this means for our own numbers</h2>

        <p>
          Our certified entries reach accuracies well below what sampling can resolve. One LiH
          entry certifies at <strong>0.096 mHartree</strong>; the sampling spread on that circuit at
          100,000 shots per evaluation is around <strong>2.5 mHartree</strong>, roughly 26 times
          larger. Resolving the certified figure would need on the order of 10⁷ shots per
          evaluation, and a run needs thousands of evaluations.
        </p>

        <p>
          That is not an argument against noiseless benchmarking — you cannot attribute a failure
          to the ansatz if sampling is free to move the answer. But a certified gap is a statement
          about an algorithm, not a prediction about a device, and we would rather say so.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Limits, including one we caused</h2>

        <p>
          We fixed the ansatz at <span className="font-mono text-xs">reps=2</span> for every
          molecule, while the suite tunes depth per molecule — our certified N₂ entry uses
          reps=10. So N₂ and benzene fail here at <em>exact</em> evaluation (743 and 201 mHartree
          against certified values of 4.5 and 8.7), which makes 180 of the 780 runs useless for
          their intended purpose. They are reported above rather than deleted, as a negative result
          about ansatz capacity. H₄ and C₄H₄ sit in between: usable, but their noiseless baselines
          are poor enough that noise degradation is not cleanly attributable.
        </p>

        <p>
          Also: eight molecules, one ansatz family, three optimizers, ten seeds, sampling noise
          only. No gate noise, no readout error, no error mitigation, no hardware.
        </p>

        <p>
          One curiosity we cannot yet explain: on C₄H₄, Adam gets <em>better</em> as noise
          increases — 20.3 mHartree exact, 18.6 at 10,000 shots, 14.5 at 1,000, all at ten seeds.
          Both molecules where we see this have poor noiseless baselines, which fits noise kicking
          the optimizer out of a bad basin. We are not claiming it on two cases.
        </p>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm font-semibold text-foreground mb-2">Check it yourself</p>
          <p className="text-sm text-muted-foreground leading-6 mb-3">
            All 780 runs are published, including every trapped seed and every failure. The
            Hamiltonians come from certified entries in the same repository and each run records
            its seeds, so any number here can be regenerated.
          </p>
          <div className="text-sm space-x-4">
            <Link href="/blog/vqe-reproducibility-threading-bug" className="text-primary hover:underline">
              The threading finding →
            </Link>
            <Link href="/leaderboard" className="text-primary hover:underline">
              Leaderboard →
            </Link>
            <a href="https://github.com/qencode-benchmark/qencode-benchmark"
              target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
              GitHub →
            </a>
          </div>
        </div>

      </div>
    </main>
  );
}
