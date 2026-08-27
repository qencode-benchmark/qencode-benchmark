import Link from "next/link";

export const metadata = {
  title: "The Optimal Shot Allocation Rule Made Our Energies 50× Worse",
  description:
    "Neyman allocation is the textbook variance-minimising way to split a VQE shot budget across Pauli terms. Estimated from a pilot sample it is catastrophically biased — it silently deletes the largest-coefficient terms. Two cheap fixes recover a validated 2.3× shot saving.",
  alternates: { canonical: "/blog/shot-allocation-neyman-trap" },
  openGraph: {
    title: "The Optimal Shot Allocation Rule Made Our Energies 50× Worse",
    description:
      "The variance-minimising shot allocation for VQE has a trap: a pilot-estimated standard deviation of exactly zero deletes a term from the energy entirely, and it happens to the terms that matter most. 270 runs, 10 molecules, and the fix.",
    url: "https://www.qencode-benchmark.org/blog/shot-allocation-neyman-trap",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "The Optimal Shot Allocation Rule Made Our Energies 50× Worse",
  description:
    "Neyman allocation splits a measurement budget in proportion to each term's coefficient times its standard deviation. In VQE the standard deviation must be estimated from a pilot sample, and that estimate is exactly zero whenever the pilot comes out all-heads or all-tails — which starves near-deterministic terms of shots and drops them from the energy. Those terms carry 9.1× the mean coefficient. Shrinkage plus pooling fixes it and yields a validated 2.3× shot saving.",
  datePublished: "2026-08-27",
  dateModified: "2026-08-27",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/shot-allocation-neyman-trap",
  keywords: [
    "shot allocation", "Neyman allocation", "VQE shot budget", "measurement problem",
    "Pauli term sampling", "variance reduction", "Rosalin", "weighted random sampling",
    "quantum chemistry benchmark", "variational quantum eigensolver", "estimator bias",
    "Agresti-Coull", "QEncode",
  ],
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What is Neyman allocation in VQE?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "A VQE energy is a weighted sum over Pauli terms, E = sum_i c_i <P_i>, and each term must be sampled separately. Neyman allocation gives term i a share of the shot budget proportional to |c_i| times sigma_i, its standard deviation. That is the split which minimises the variance of a weighted sum of independent estimators. It beats uniform allocation because term variances are wildly unequal: a Pauli string close to an eigenoperator of the current state has sigma near zero, so shots spent on it buy nothing.",
      },
    },
    {
      "@type": "Question",
      name: "Why does Neyman shot allocation fail in practice?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Because sigma is not known in advance and must be estimated from a pilot sample. The estimate sqrt(1 - m^2) is exactly zero whenever the pilot draw comes out all-heads or all-tails, which is likely for a near-deterministic term. A term with an estimated sigma of zero receives zero shots and is silently dropped from the energy sum. Near-deterministic Pauli strings tend to carry large coefficients, so the rule preferentially discards the terms that matter most. In our measurements the deleted terms carried 9.1 times the mean coefficient and a median of 48 percent of the Hamiltonian one-norm, producing a median error of 604 mHa against 11.4 mHa for plain uniform allocation.",
      },
    },
    {
      "@type": "Question",
      name: "How do you fix biased Neyman shot allocation?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Two cheap repairs. First, shrink the variance estimate: use the Agresti-Coull proportion p = (k+1)/(pilot+2), which is never exactly 0 or 1, so the estimated sigma is never exactly zero and no term is ever starved; add a floor of one shot per term. Second, pool the pilot sample with the main measurement pass instead of discarding it — the pilot is already paid for. Together these give a 1.53x reduction in RMSE over uniform allocation, which is 2.3x fewer shots for the same accuracy, and they win in 84 of 90 test configurations.",
      },
    },
    {
      "@type": "Question",
      name: "Why should shot allocation be judged on RMSE rather than standard deviation?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Because a scheme that starves a term of shots drops it from the estimate entirely, and that is bias, not spread. Bias does not appear in the standard deviation. Naive Neyman allocation has the smallest standard deviation of any scheme we tested — its estimates are tightly clustered — but they are clustered hundreds of millihartree away from the true energy. Judged on standard deviation it looks like the winner; judged on RMSE it is fifty times worse than doing nothing clever at all.",
      },
    },
  ],
};

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
          <time dateTime="2026-08-27">August 27, 2026</time>
          <span>·</span>
          <span>9 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          The Optimal Shot Allocation Rule Made Our Energies 50× Worse
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Neyman allocation is the textbook answer to how you should split a measurement
          budget. It is provably variance-minimising, it is easy to implement, and when we
          applied it to VQE energies it produced errors of six hundred millihartree —
          against eleven for the naive scheme it was supposed to beat. The failure turned
          out to be more interesting than the speedup, and the fix is four lines.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            Splitting shots in proportion to <strong>|c<sub>i</sub>| σ<sub>i</sub></strong>{" "}
            is optimal — but σ has to be estimated, and the obvious estimator returns{" "}
            <strong>exactly zero</strong> whenever a pilot sample comes out all-heads or
            all-tails. A term with σ̂ = 0 gets zero shots and vanishes from the energy.
            Those are disproportionately the <em>large</em> terms: they carried{" "}
            <strong>9.1× the mean coefficient</strong> and a median of{" "}
            <strong>48% of the Hamiltonian one-norm</strong>. Shrinking the estimate and
            pooling the pilot into the final average fixes it, and gives a validated{" "}
            <strong>2.3× shot saving</strong> across 10 molecules.
          </p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">The measurement problem</h2>

        <p>
          A VQE energy is not measured. It is assembled from pieces:{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">E = Σᵢ cᵢ ⟨Pᵢ⟩</code>,
          a weighted sum over the Pauli terms of the Hamiltonian. Benzene has 914 of them;
          H₆ has 919. Each ⟨Pᵢ⟩ has to be estimated by repeatedly preparing the state and
          measuring, and every one of those repetitions — every <em>shot</em> — costs real
          time on real hardware. The shot budget is the dominant cost of running VQE, and
          it is the reason VQE is hard to scale.
        </p>

        <p>
          So: given a budget of N shots, how many should each term get? The default in most
          code is to divide evenly. That is obviously not optimal, because the terms are not
          equally uncertain. A Pauli string that happens to be close to an eigenoperator of
          the current state returns nearly the same answer every time — its σᵢ is nearly
          zero — and shots spent on it buy nothing at all.
        </p>

        <p>
          Statistics has a name for the right answer here, and it is a century old.{" "}
          <strong>Neyman allocation</strong> gives each term a share proportional to{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">|cᵢ| σᵢ</code>. For a
          weighted sum of independent estimators that provably minimises the variance, and
          the improvement over uniform is exactly the spread in |cᵢ|σᵢ across terms — which
          in molecular Hamiltonians is large. PennyLane ships a related idea as Rosalin,
          which weights by |cᵢ| alone.
        </p>

        <p>
          The distinction matters more than it looks. Weighting by |cᵢ| is blind to variance,
          so it happily pours shots into a large-coefficient term that is already known to
          four decimal places. That is the gap Neyman allocation closes — in principle.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What we measured</h2>

        <p>
          270 runs: 10 molecules from 20 to 919 Pauli terms, three parameter states each,
          three shot budgets, 200 repeats per scheme so the error distribution is actually
          resolved rather than guessed at.
        </p>

        <p>
          The three states matter, and they are the part we got wrong the first time. Term
          variances depend on the quantum state, so an advantage measured at a random
          starting point tells you very little about the regime an optimiser actually spends
          its time in. We measured at a random start, 40 steps in, and fully converged —
          each found by exact statevector optimisation, so no sampling contaminates the
          choice of state.
        </p>

        <p>
          Every scheme is charged the <em>same</em> total budget, and shots are counted per
          term so the total is exactly Σsᵢ. Neyman pays for its own pilot out of that budget.
          We also ran an <em>oracle</em> variant using the exact σᵢ from the statevector — not
          a usable method, but it marks the ceiling.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">It looked like a triumph</h2>

        <p>
          Our first pass measured the standard deviation of each scheme, and Neyman
          allocation won everything. On LiH it cut the spread from 15.9 mHa to 1.8 — nearly
          nine times tighter than uniform, at identical cost. We had a headline.
        </p>

        <p>
          It survived the obvious checks, too. The measured spreads matched the closed-form
          Neyman variance to within sampling noise, so the effect was not a fluke of one
          random draw; it was the theory working exactly as advertised.
        </p>

        <p>
          The headline was false. Standard deviation measures how tightly the estimates
          cluster; it says nothing about <em>where</em> they cluster. Once we scored the same
          runs on RMSE, which counts bias as the error it is, Neyman allocation was not the
          best scheme in the study. It was by far the worst:
        </p>

        <div className="rounded-md border not-prose overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/60">
              <tr className="text-left">
                <th className="px-3 py-2 font-semibold">scheme</th>
                <th className="px-3 py-2 font-semibold text-right">median std</th>
                <th className="px-3 py-2 font-semibold text-right">median RMSE</th>
                <th className="px-3 py-2 font-semibold text-right">beats uniform</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr className="border-t">
                <td className="px-3 py-2">uniform</td>
                <td className="px-3 py-2 text-right">11.36 mHa</td>
                <td className="px-3 py-2 text-right">11.35 mHa</td>
                <td className="px-3 py-2 text-right text-muted-foreground">—</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2">weighted (|cᵢ|)</td>
                <td className="px-3 py-2 text-right">9.70 mHa</td>
                <td className="px-3 py-2 text-right">9.68 mHa</td>
                <td className="px-3 py-2 text-right">58/90</td>
              </tr>
              <tr className="border-t bg-destructive/5">
                <td className="px-3 py-2 font-semibold">Neyman (pilot σ̂)</td>
                <td className="px-3 py-2 text-right font-semibold">5.75 mHa</td>
                <td className="px-3 py-2 text-right font-semibold">603.70 mHa</td>
                <td className="px-3 py-2 text-right font-semibold">22/90</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p className="text-sm text-muted-foreground">
          The tightest estimates in the study — a median spread half that of uniform — and
          centred six-tenths of a hartree away from the right answer. Chemical accuracy is
          1.6 mHa.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The trap</h2>

        <p>
          A Pauli operator has eigenvalues ±1, so its variance is{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">σ² = 1 − ⟨P⟩²</code> and
          you estimate it by measuring ⟨P⟩ on a small pilot sample. Draw{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">k</code> heads out of{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">n</code>, set{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">m = (2k − n)/n</code>,
          take <code className="font-mono text-xs bg-muted px-1 rounded">σ̂ = √(1 − m²)</code>.
        </p>

        <p>
          When the pilot comes out <em>all</em> heads or <em>all</em> tails, m = ±1 and
          σ̂ is <strong>exactly zero</strong>. Not small — zero. That term is then allocated
          zero shots, is never measured, and contributes nothing to the energy. Its
          coefficient is simply deleted from the Hamiltonian.
        </p>

        <p>
          And which terms come out all-heads? The near-deterministic ones — precisely the
          terms whose true σ is genuinely small. That much is self-consistent and sounds
          harmless. The problem is what those terms are: in a molecular Hamiltonian near a
          Hartree-Fock-like state, the near-deterministic Pauli strings are the Z-type
          diagonal terms, and those carry the <em>largest</em> coefficients in the whole
          operator.
        </p>

        <div className="rounded-lg border-l-4 border-destructive bg-destructive/5 p-5 not-prose">
          <p className="text-sm text-foreground leading-6">
            Across the 70 configurations where at least one term was deleted, the deleted
            terms carried <strong>9.1× the mean |cᵢ|</strong> of the terms that survived. A
            median of <strong>48% of λ = Σ|cᵢ|</strong> was silently removed from the energy.
            The rule is not merely lossy — it is <em>selectively</em> lossy, and it selects
            for importance.
          </p>
        </div>

        <p>
          The oracle version confirms the diagnosis. Given the exact σᵢ it funds every term,
          has essentially zero bias, and does beat uniform. So the allocation rule is fine.
          What is broken is the estimator of σ — and nothing about that is specific to
          quantum computing. It is a small-sample estimation failure that happens to be
          catastrophic here because the consequence of σ̂ = 0 is not a bad estimate but no
          estimate at all.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The fix</h2>

        <p>
          Two repairs, both cheap, and neither of them clever:
        </p>

        <p>
          <strong>1. Shrink the variance estimate.</strong> Use the Agresti-Coull proportion{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">p = (k + 1)/(n + 2)</code>{" "}
          instead of k/n. It is never exactly 0 or 1, so σ̂ is never exactly zero, so no term
          is ever starved. Add a floor of one shot per term for good measure.
        </p>

        <p>
          <strong>2. Pool the pilot with the main pass.</strong> The pilot already measured
          every term and you already paid for it. Discarding it is pure waste. Combine the
          two samples per term, weighted by shot count.
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="text-muted-foreground"># the whole fix</p>
          <p>p_ac  = (k + 1.0) / (n_pilot + 2.0)      <span className="text-muted-foreground"># never 0 or 1</span></p>
          <p>sigma = 2.0 * np.sqrt(p_ac * (1.0 - p_ac))</p>
          <p>alloc = floor(|c| * sigma / sum(|c| * sigma) * budget) + 1</p>
          <p>mean  = (n_pilot * m_pilot + s * m_main) / (n_pilot + s)</p>
        </div>

        <p>Scored on RMSE, over the same 270 runs:</p>

        <div className="rounded-md border not-prose overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/60">
              <tr className="text-left">
                <th className="px-3 py-2 font-semibold">scheme</th>
                <th className="px-3 py-2 font-semibold text-right">median RMSE</th>
                <th className="px-3 py-2 font-semibold text-right">vs uniform</th>
                <th className="px-3 py-2 font-semibold text-right">beats uniform</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr className="border-t">
                <td className="px-3 py-2">uniform</td>
                <td className="px-3 py-2 text-right">11.35 mHa</td>
                <td className="px-3 py-2 text-right">1.00×</td>
                <td className="px-3 py-2 text-right text-muted-foreground">—</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2">weighted (|cᵢ|)</td>
                <td className="px-3 py-2 text-right">9.68 mHa</td>
                <td className="px-3 py-2 text-right">1.17×</td>
                <td className="px-3 py-2 text-right">58/90</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2 text-destructive">naive Neyman</td>
                <td className="px-3 py-2 text-right text-destructive">603.70 mHa</td>
                <td className="px-3 py-2 text-right text-destructive">0.04×</td>
                <td className="px-3 py-2 text-right text-destructive">22/90</td>
              </tr>
              <tr className="border-t">
                <td className="px-3 py-2">+ shrinkage</td>
                <td className="px-3 py-2 text-right">8.88 mHa</td>
                <td className="px-3 py-2 text-right">1.45×</td>
                <td className="px-3 py-2 text-right">81/90</td>
              </tr>
              <tr className="border-t bg-primary/5">
                <td className="px-3 py-2 font-semibold">+ shrinkage + pooling</td>
                <td className="px-3 py-2 text-right font-semibold">8.49 mHa</td>
                <td className="px-3 py-2 text-right font-semibold">1.53×</td>
                <td className="px-3 py-2 text-right font-semibold">84/90</td>
              </tr>
              <tr className="border-t text-muted-foreground">
                <td className="px-3 py-2">oracle (exact σ)</td>
                <td className="px-3 py-2 text-right">7.41 mHa</td>
                <td className="px-3 py-2 text-right">1.69×</td>
                <td className="px-3 py-2 text-right">86/90</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p>
          Because sampling variance falls as 1/N, a 1.53× reduction in RMSE is{" "}
          <strong>2.33× fewer shots</strong> for the same accuracy. The pilot costs only 6%
          above the oracle ceiling — knowing the variances exactly would buy you almost
          nothing more.
        </p>

        <p>
          And it is not carried by one lucky molecule. It holds in every one of the ten,
          from 20 terms to 919:
        </p>

        <div className="rounded-md border not-prose overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-muted/60">
              <tr className="text-left">
                <th className="px-3 py-2 font-semibold">molecule</th>
                <th className="px-3 py-2 font-semibold text-right">terms</th>
                <th className="px-3 py-2 font-semibold text-right">RMSE gain</th>
                <th className="px-3 py-2 font-semibold text-right">shot saving</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {[
                ["BeH₂", 20, "1.26×", "1.6×"],
                ["H₂O", 62, "1.61×", "2.6×"],
                ["H₄", 132, "1.25×", "1.6×"],
                ["NH₃", 132, "1.58×", "2.5×"],
                ["LiH", 155, "1.99×", "4.0×"],
                ["water dimer", 155, "1.86×", "3.5×"],
                ["C₄H₄", 185, "1.77×", "3.1×"],
                ["N₂", 378, "1.39×", "1.9×"],
                ["benzene", 914, "1.62×", "2.6×"],
                ["H₆", 919, "1.45×", "2.1×"],
              ].map(([m, t, g, s]) => (
                <tr key={m} className="border-t">
                  <td className="px-3 py-2">{m}</td>
                  <td className="px-3 py-2 text-right text-muted-foreground">{t}</td>
                  <td className="px-3 py-2 text-right">{g}</td>
                  <td className="px-3 py-2 text-right">{s}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p>
          It also holds across the optimisation trajectory — 1.46× at a random start, 2.07×
          mid-optimisation, 1.32× converged — and across budgets from 10⁴ to 10⁶ shots.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">A correction</h2>

        <p>
          A post we published earlier this month, and have since withdrawn, reported{" "}
          <strong>8.9×</strong> for Neyman allocation on LiH. That number was wrong in three
          ways, and this study was built to find out whether it was:
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            It was measured at a <strong>random starting point</strong>, not where an
            optimiser actually works. The same molecule gives 2.0× once converged.
          </li>
          <li>
            It compared <strong>standard deviation only</strong>, so the bias described
            above was invisible. Scored on RMSE the scheme was fifty times worse than
            uniform, not nine times better.
          </li>
          <li>
            It rested on <strong>two molecules and one parameter point</strong>.
          </li>
        </ul>

        <p>
          The validated figure is ~1.5× in RMSE, ~2.3× in shots. That is a smaller and much
          duller number than 8.9×, and it is the one we can defend. We would rather publish
          the dull number and the failure that produced it than keep the exciting one.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What this does not show</h2>

        <p>
          Stated plainly, because a result like this invites overreading:
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            Shots are counted <strong>per term</strong>. Grouping commuting terms into
            joint measurements is a separate and larger saving; it composes with any of
            these schemes and is not modelled here. No claim above depends on it.
          </li>
          <li>
            This measures the <strong>energy estimator</strong>, not a full optimisation
            run. Whether a 2.3× cheaper estimator makes VQE converge faster or more reliably
            is a different question, and we have not answered it.
          </li>
          <li>
            Statevector simulation throughout — <strong>no gate noise</strong>, no readout
            error, no device topology. Sampling noise is zero-mean; gate noise is not.
          </li>
        </ul>

        <p>
          One methodological note. Terms are sampled from{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">Binomial(s, (1+⟨P⟩)/2)</code>{" "}
          rather than by executing the circuit s times. For a ±1 observable that is the exact
          sampling distribution, not an approximation, and it is what makes 200 repeats
          across 919 terms affordable. We tested that claim rather than asserting it: both
          paths agree within sampling noise. The check is in the repository.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The general lesson</h2>

        <p>
          The bug here was not in the allocation rule, which is correct, nor really in the
          variance estimator, which is standard. It was in the <em>metric</em>. We measured
          spread, spread is what an allocation scheme is designed to reduce, and a scheme
          that reduces spread by quietly deleting half the Hamiltonian scored beautifully.
        </p>

        <p>
          Any optimality argument that assumes a quantity is known — and{" "}
          <em>every</em> optimal-allocation argument assumes σ is known — becomes a claim
          about your estimator the moment you implement it. That is where it can fail, and
          it can fail in a direction the optimality proof never mentions.
        </p>

        <p>
          All 270 runs, the raw cluster logs, the tooling and the sampling-model check are in
          the repository under{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">experiments/shot_allocation/</code>.
          Failed and superseded runs are included, as always.
        </p>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm text-muted-foreground leading-6">
            QEncode is an open benchmark for reproducible VQE quantum chemistry. Every entry
            records its full provenance — Hamiltonian, ansatz, optimiser, seed, package
            versions and code commit — so results can be independently rebuilt. See the{" "}
            <Link href="/leaderboard" className="text-primary hover:underline">leaderboard</Link>{" "}
            or read{" "}
            <Link href="/blog/vqe-reproducibility-scorecard" className="text-primary hover:underline">
              the four conditions a reproducible VQE result has to meet
            </Link>.
          </p>
        </div>
      </div>
    </main>
  );
}
