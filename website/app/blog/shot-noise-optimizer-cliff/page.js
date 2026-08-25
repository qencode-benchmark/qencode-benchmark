import Link from "next/link";

export const metadata = {
  title: "We Added Shot Noise to Our Own Benchmark and One Optimizer Fell Off a Cliff",
  description:
    "480 VQE runs on published QEncode Hamiltonians. COBYLA degrades 2,510x under 1,000-shot sampling. L-BFGS-B is fine on a 62-term Hamiltonian and collapses 169x on a 155-term one. Adam is robust on both. The shot budget a gradient optimizer needs scales with the Hamiltonian, not the molecule.",
  alternates: { canonical: "/blog/shot-noise-optimizer-cliff" },
  openGraph: {
    title: "We Added Shot Noise to Our Own Benchmark and One Optimizer Fell Off a Cliff",
    description:
      "Same optimizer, same shot budget, two molecules: one degrades 2x, the other collapses 169x. Why published optimizer comparisons disagree with each other.",
    url: "https://www.qencode-benchmark.org/blog/shot-noise-optimizer-cliff",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "We Added Shot Noise to Our Own Benchmark and One Optimizer Fell Off a Cliff",
  description:
    "480 seeded VQE runs measuring how COBYLA, L-BFGS-B and Adam degrade under finite-shot sampling on published QEncode Hamiltonians. The shot budget a gradient-based optimizer needs scales with Hamiltonian size.",
  datePublished: "2026-08-25",
  dateModified: "2026-08-25",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/shot-noise-optimizer-cliff",
  keywords: [
    "VQE shot noise", "COBYLA", "L-BFGS-B", "Adam optimizer", "parameter-shift gradients",
    "finite sampling", "quantum chemistry benchmark", "variational quantum eigensolver",
    "optimizer comparison", "Hamiltonian 1-norm", "QEncode",
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
        text: "In our measurements Adam, which is built for stochastic gradients, was the most robust: it degraded about 20x going from exact energies to 1,000 shots per evaluation, and never landed in a bad local minimum across 40 runs at that budget. L-BFGS-B was equally good on a small Hamiltonian but collapsed on a larger one. COBYLA, a gradient-free trust-region method, degraded roughly 2,510x and failed in every one of ten seeds at 1,000 shots. The ranking depends on the shot budget and the size of the Hamiltonian, which is why published comparisons disagree.",
      },
    },
    {
      "@type": "Question",
      name: "Why do published VQE optimizer comparisons contradict each other?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Because the answer depends on two things papers often do not foreground: the type of noise and the shot budget relative to the Hamiltonian size. A study using device or gate noise measures a biased but smooth objective, where COBYLA does comparatively well. A study using finite sampling measures a stochastic objective, where COBYLA does badly. Separately, a gradient-based method such as L-BFGS-B works well above a shot threshold and collapses below it, and that threshold rises with the number of Pauli terms in the Hamiltonian. Two studies can therefore rank the same optimizer oppositely and both be correct.",
      },
    },
    {
      "@type": "Question",
      name: "How many shots does a VQE run need?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "It depends on the Hamiltonian, not just the molecule. On a 62-term water Hamiltonian, L-BFGS-B was essentially unaffected between 10,000 and 1,000 shots per energy evaluation, degrading only 2x. On a 155-term lithium hydride Hamiltonian the same method over the same range degraded 169x and failed in all ten seeds. Sampling error in the energy grows with the number of terms being estimated, so the shot budget a gradient-based optimizer needs scales with Hamiltonian size rather than with how correlated the molecule is.",
      },
    },
    {
      "@type": "Question",
      name: "Can a noiseless VQE benchmark tell you anything about hardware?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "It tells you about the algorithm, which is what it is for, but it does not tell you what finite sampling will do. Our certified entries reach accuracies far below the shot-noise floor at realistic budgets: one entry certifies at 0.096 mHartree while the sampling spread at 100,000 shots per evaluation is about 2.5 mHartree, roughly 26 times larger. Isolating algorithm quality from sampling is a deliberate design choice, but a noiseless number should not be read as a hardware prediction.",
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
          <span>·</span><span>9 min read</span><span>·</span><span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          We Added Shot Noise to Our Own Benchmark and One Optimizer Fell Off a Cliff
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Every QEncode entry is computed with exact statevector arithmetic. That is deliberate:
          it isolates the algorithm from sampling and hardware error. But it invites an obvious
          question, and it is the one we get asked most: what happens when you cannot measure an
          energy exactly? So we measured it — 480 runs, on the same Hamiltonians our published
          entries use.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            Under 1,000-shot sampling, <strong>COBYLA degraded 2,510×</strong> and failed in all ten
            seeds. <strong>Adam degraded 20×</strong> and never failed. <strong>L-BFGS-B did both</strong>:
            barely affected on a 62-term Hamiltonian, collapsed 169× on a 155-term one. The shot budget
            a gradient-based optimizer needs scales with <em>the size of the Hamiltonian</em>, not with
            how hard the molecule is. That single fact explains why published optimizer comparisons
            contradict each other.
          </p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">How the experiment was built</h2>

        <p>
          The Hamiltonians are not new. Each published QEncode entry stores its complete Pauli
          decomposition, so we reconstructed the operators directly from the artifacts — the exact
          ground state of the reconstructed Hamiltonian agrees with the stored value to{" "}
          <span className="font-mono text-xs">2.7e-15</span> Hartree. Anyone can do the same from the
          public repository.
        </p>

        <p>
          On top of each Hamiltonian we ran a hardware-efficient ansatz started from the Hartree-Fock
          determinant, matching the suite&rsquo;s own construction, and optimized it with three
          methods across three sampling regimes and ten random seeds each. Every run was
          single-threaded, with the sampling RNG seeded, so every number below is reproducible.
        </p>

        <p>
          One methodological point that mattered more than anything else: <strong>we calibrated the
          optimizers at zero noise first.</strong> Our first attempt had Adam at 292 mHartree against
          COBYLA&rsquo;s 0.73 with no noise at all — an unequal iteration budget, not a finding. Had
          we skipped that check we would have published &ldquo;gradient methods collapse under shot
          noise&rdquo; backwards. In the results below all three methods land within 0.06 mHartree of
          each other on water at exact evaluation, so every later difference is sampling and nothing
          else.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Water: COBYLA falls apart, the others do not</h2>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            H₂O, [4,4] active space, 62 Pauli terms — median gap, mHa (10 seeds; Adam pools 2 budgets, n=20)
          </p>
          <p>shots        Adam     L-BFGS-B     COBYLA</p>
          <p>exact       0.341        0.387      0.402   &lt;- matched, budget is fair</p>
          <p>10,000      1.160        4.388     48.704</p>
          <p>1,000       6.837        9.144   1009.836</p>
          <p className="mt-2">degradation   20x          24x      2510x</p>
        </div>

        <p>
          At 1,000 shots COBYLA failed in <strong>ten out of ten seeds</strong>, landing above 100
          mHartree every time. Adam failed in none. This is the clean comparison in the whole study:
          identical Hamiltonian, identical ansatz, identical starting distribution, and all three
          methods provably converged before noise was introduced.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Lithium hydride: the cliff</h2>

        <p>
          Then the same experiment on a larger Hamiltonian produced something we did not predict.
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            L-BFGS-B only — same method, same budgets, two molecules
          </p>
          <p>molecule   terms    10,000 shots    1,000 shots     ratio</p>
          <p>H₂O           62           4.388          9.144        2x</p>
          <p>LiH          155           4.145        700.100      169x</p>
        </div>

        <p>
          At 10,000 shots the two are indistinguishable. Drop to 1,000 and water barely moves while
          lithium hydride collapses — ten seeds out of ten above 100 mHartree. Adam over the same
          range went from 1.07 to 4.94 mHartree, with no failures.
        </p>

        <p>
          The mechanism is not exotic. L-BFGS-B builds a curvature model from gradients; with
          parameter-shift evaluation each gradient component is itself a sampled quantity. Estimating
          an energy means estimating a sum over Pauli terms, so at a fixed shot budget the sampling
          error grows with the number of terms. Past some point the gradients stop carrying usable
          curvature information and a quasi-Newton method has nothing left to work with. Adam does
          not build a curvature model, so it degrades smoothly instead of falling over.
        </p>

        <p>
          The practical consequence is a rule of thumb worth stating plainly:{" "}
          <strong>the shot budget a gradient-based optimizer needs is set by the size of your
          Hamiltonian, not by how correlated your molecule is.</strong> A method validated on a small
          active space can fail on a larger one at the same shot count, with no warning.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why the literature disagrees with itself</h2>

        <p>
          Before drawing conclusions we checked what was already published, and found the field
          split. One benchmark of optimizers for quantum chemistry — covering H₂, LiH, BeH₂, H₂O and
          HF, essentially our molecules — reports that{" "}
          <em>&ldquo;in noisy quantum circuit conditions, SPSA, POWELL, and COBYLA are among the
          best-performing optimizers&rdquo;</em>. Other work reports the opposite, that COBYLA and
          Nelder-Mead are among the most heavily damaged by noise.
        </p>

        <p>
          Our data reconciles them, and the resolution is mundane. First, <strong>noise type</strong>:
          gate and decoherence noise bias a smooth objective, which a trust-region method tolerates;
          finite sampling makes the objective stochastic, which it does not. Second,{" "}
          <strong>what the comparison is against</strong>: COBYLA looks strong beside deterministic
          quasi-Newton methods that break on noisy gradients, and weak beside a stochastic optimizer.
          Third, <strong>shot budget versus Hamiltonian size</strong>, as above. Two careful studies
          can rank the same optimizer oppositely and both be right.
        </p>

        <p>
          We want to be clear that none of this is a novel discovery. Optimizer robustness under
          noise is well-studied. What we think is useful here is the controlled contrast — one
          Hamiltonian family, matched noiseless baselines, seeded sampling, every run published —
          which turns a disagreement between papers into a statement about when each answer applies.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What this means for our own numbers</h2>

        <p>
          It reframes them, and not flatteringly. Our certified entries reach accuracies well below
          what sampling can resolve at realistic budgets. One LiH entry certifies at{" "}
          <strong>0.096 mHartree</strong>; the sampling spread on that same circuit at 100,000 shots
          per energy evaluation is about <strong>2.5 mHartree</strong> — roughly 26 times larger.
          Resolving the certified figure would take on the order of 10⁷ shots per evaluation, and a
          VQE run needs thousands of evaluations.
        </p>

        <p>
          That is not an argument against noiseless benchmarking. Separating algorithmic accuracy
          from sampling is exactly why the suite is defined the way it is, and you cannot attribute a
          failure to the ansatz if shot noise is free to move the answer. But a certified gap is a
          statement about an algorithm, not a prediction about a device, and we would rather say so
          than let the number be read as more than it is.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What we got wrong</h2>

        <p>
          Three predictions, recorded before measuring, and the data overturned all of them.
        </p>

        <ul className="list-disc pl-6 space-y-1">
          <li>
            We predicted <strong>both</strong> optimizer families would degrade under sampling, since
            parameter-shift gradients are sampled too. Adam barely degrades.
          </li>
          <li>
            We predicted L-BFGS-B would <strong>collapse like COBYLA</strong>, reconciling the
            literature neatly. It collapses on one molecule and is fine on the other.
          </li>
          <li>
            At 88% of the runs complete we reported a clean three-way ordering on water. At full
            statistics <strong>it disappeared</strong> — L-BFGS-B came in at 9.1 mHartree, not the
            65.6 the partial data showed, statistically tied with Adam.
          </li>
        </ul>

        <p>
          The last one is the reason to run every seed before publishing. A partial result that looks
          tidy is the most dangerous kind.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Limits</h2>

        <p>
          Two molecules, one ansatz family, three optimizers, ten seeds. Shot noise only — no gate
          error, no readout error, no error mitigation. COBYLA on LiH fails even at exact evaluation
          (61 mHartree), so its degradation there is not cleanly attributable to sampling, and we
          have not used it for any claim. The threshold we describe is bracketed between 1,000 and
          10,000 shots on two Hamiltonians; we have not located it precisely, and we do not know its
          functional form.
        </p>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm font-semibold text-foreground mb-2">Check it yourself</p>
          <p className="text-sm text-muted-foreground leading-6 mb-3">
            All 480 runs are published, including the failures — every trapped seed, every
            catastrophic gap. The Hamiltonians come from the certified entries in the same
            repository, and each run records its seeds, so any number here can be regenerated.
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
