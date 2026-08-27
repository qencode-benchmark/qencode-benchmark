import Link from "next/link";

export const metadata = {
  title: "What These Numbers Mean",
  description:
    "A plain guide to reading the QEncode leaderboard: what the energy gap is measured against, what the CCSD(T) column tells you, the difference between two-qubit gate counts and T-gate estimates, and what these numbers deliberately do not claim.",
  alternates: { canonical: "/leaderboard/guide" },
  openGraph: {
    title: "What These Numbers Mean — Reading the QEncode Leaderboard",
    description:
      "Energy gap, classical baseline, near-term gate counts, fault-tolerant T-gate estimates, and the Pareto front — what each column measures and what it does not.",
    url: "https://www.qencode-benchmark.org/leaderboard/guide",
    type: "article",
  },
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What is the energy gap on the QEncode leaderboard measured against?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "The gap is the absolute difference between the VQE energy and the exact ground-state energy of the same qubit Hamiltonian, obtained by exact diagonalisation (CASCI) in the same active space, reported in millihartree. It is not measured against experiment and not against a complete-basis-set limit. That is deliberate: it isolates the error contributed by the quantum algorithm from the much larger errors contributed by the basis set and the choice of active space, which every method in the comparison shares equally.",
      },
    },
    {
      "@type": "Question",
      name: "Does VQE beat classical methods on the QEncode leaderboard?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Generally no, and the leaderboard is built to make that visible rather than to hide it. CCSD(T) is the classical gold standard for molecules of this size and it remains cheaper and more accurate than VQE across the suite. The Beats Classical flag is set only when the VQE correlation energy exceeds the CCSD(T) correlation energy for the same system. The purpose of the benchmark is to measure how far quantum algorithms are from that bar and whether they are moving, under conditions that can be independently reproduced.",
      },
    },
    {
      "@type": "Question",
      name: "What is the difference between two-qubit gate count and T-gate estimate?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "They price two different eras of hardware. The two-qubit gate count and circuit depth are the near-term cost: on today's noisy devices the two-qubit gate is the dominant error source, so that count sets whether a circuit is runnable now. The T-gate estimate is the fault-tolerant cost: in an error-corrected machine Clifford gates are comparatively cheap and non-Clifford T gates dominate, so that count sets the runtime of a future error-corrected implementation. A circuit can look cheap on one axis and expensive on the other.",
      },
    },
    {
      "@type": "Question",
      name: "How are the T-gate estimates on QEncode calculated?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "They are derived by classical post-processing of the stored Pauli decomposition, not measured. The method is qubitized quantum phase estimation: from the Hamiltonian one-norm lambda, the number of walk operator applications needed for a target precision is ceil(pi*lambda/(2*epsilon)); each walk step costs about 2L+mu Toffoli gates for L Pauli terms; and each Toffoli is four T gates. Logical qubit counts follow from the system register plus the index and coefficient registers. Wall-clock runtime is deliberately not published, because it would require assuming a code distance and a physical error rate, and those assumptions would dominate the answer.",
      },
    },
    {
      "@type": "Question",
      name: "What does the Pareto-optimal badge mean on the leaderboard?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "An entry is Pareto-optimal, or non-dominated, when no other entry for the same molecule is better on both accuracy and hardware cost at once. It marks the entries that represent a genuine trade-off rather than a strictly worse choice. Any entry without the badge is beaten on both axes by something else in the table, so there is no configuration under which it is the right pick for that molecule.",
      },
    },
  ],
};

function Row({ name, sub, children }) {
  return (
    <div className="rounded-lg border p-5 not-prose">
      <div className="flex items-baseline gap-3 flex-wrap mb-2">
        <span className="text-sm font-semibold text-foreground">{name}</span>
        {sub && <span className="text-xs text-muted-foreground font-mono">{sub}</span>}
      </div>
      <div className="text-sm text-muted-foreground leading-6 space-y-2">{children}</div>
    </div>
  );
}

export default function GuidePage() {
  return (
    <main className="container max-w-2xl py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <Link
        href="/leaderboard"
        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        ← Leaderboard
      </Link>

      <div className="mt-8 mb-10">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          What These Numbers Mean
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Every column on the leaderboard answers a narrow question, and most of them are
          easy to over-read. This page says what each one measures, what it is measured
          against, and where it stops.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            An entry is one quantum chemistry calculation, run end to end, with every input
            recorded so it can be rebuilt. The <strong>gap</strong> says how close it got
            to the right answer for its own problem. The <strong>CCSD(T)</strong> column
            says how a good classical method does on the same problem — usually better.
            The <strong>gate</strong> and <strong>T-gate</strong> columns price the circuit
            on today&rsquo;s hardware and on a future error-corrected machine respectively.
          </p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">The accuracy columns</h2>

        <div className="space-y-4">
          <Row name="Gap" sub="millihartree (mHa)">
            <p>
              The absolute difference between the VQE energy and the <em>exact</em> ground
              state energy of the same qubit Hamiltonian, found by exact diagonalisation
              (CASCI) in the same active space.
            </p>
            <p>
              It is <strong>not</strong> measured against experiment, and not against a
              complete-basis-set limit. That is deliberate. A real molecule&rsquo;s energy
              error comes mostly from the basis set and the choice of active space, which
              every method in the table shares equally. Measuring against the exact answer
              for the <em>same</em> problem isolates the part the quantum algorithm is
              actually responsible for. It is a strict test of the algorithm, not a claim
              about chemistry.
            </p>
          </Row>

          <Row name="The two thresholds" sub="1.6 mHa · 10 mHa">
            <p>
              <strong>1.6 mHa</strong> is chemical accuracy — about 1 kcal/mol, roughly the
              point at which a computed reaction energy becomes useful to a chemist.
            </p>
            <p>
              <strong>10 mHa</strong> is the QEncode certification threshold. It is a
              deliberately looser bar, set so that an entry can be certified as a
              well-executed, reproducible calculation without having to also be chemically
              useful. An entry can be certified and still not be accurate enough to make a
              prediction with. The colour of the bar tells you which side of each line you
              are on.
            </p>
          </Row>

          <Row name="CCSD(T)" sub="classical baseline">
            <p>
              The correlation energy that CCSD(T) — the classical gold standard for
              molecules this size — recovers on the identical problem.
            </p>
            <p>
              <strong>It usually wins.</strong> CCSD(T) is generally both cheaper and more
              accurate than VQE across this suite, and the column exists so you can see
              that rather than have to infer it. The{" "}
              <strong>Beats Classical</strong> flag is set only when a VQE run&rsquo;s
              correlation energy exceeds the CCSD(T) correlation energy for the same system.
            </p>
            <p>
              This is the number to look at if you want to know whether quantum computing
              is useful here yet. The point of the benchmark is to measure the distance to
              that bar honestly, and whether it is closing.
            </p>
          </Row>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">The cost columns</h2>

        <p>
          These price two different eras of hardware, and a circuit can look cheap on one
          and expensive on the other.
        </p>

        <div className="space-y-4">
          <Row name="2Q gates · Depth" sub="near-term cost">
            <p>
              Two-qubit gate count and circuit depth after transpilation. On today&rsquo;s
              noisy hardware the two-qubit gate is the dominant error source, so this is
              what decides whether a circuit is runnable <em>now</em>.
            </p>
            <p>
              <strong>Blank cells are intentional.</strong> UCCSD circuits are built from
              exponential Pauli operators that stay symbolic until they are compiled for a
              specific hardware target. A raw pre-transpilation count would not be
              comparable to a real one, so it is left empty rather than filled with a
              misleading number.
            </p>
          </Row>

          <Row name="T gates" sub="fault-tolerant cost">
            <p>
              An estimate of the non-Clifford cost of solving the same Hamiltonian on an
              error-corrected machine. In that setting Clifford gates are comparatively
              cheap and T gates dominate, so this count — not the two-qubit count — sets
              the runtime.
            </p>
            <p>
              <strong>It is derived, not measured.</strong> It comes from classical
              post-processing of the stored Pauli decomposition, assuming qubitized quantum
              phase estimation: from the Hamiltonian one-norm{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">λ = Σ|h<sub>a</sub>|</code>,
              reaching precision ε needs{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">⌈πλ/2ε⌉</code>{" "}
              applications of a walk operator; each costs about{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">2L+μ</code>{" "}
              Toffoli gates for L Pauli terms; each Toffoli is four T gates.
            </p>
            <p>
              <strong>Wall-clock runtime is deliberately not published.</strong> Converting
              T gates to hours requires assuming a code distance and a physical error rate,
              and those assumptions would dominate the answer — a single number would say
              more about the assumption than about the molecule. Logical qubit counts are
              the honest stopping point.
            </p>
          </Row>

          <Row name="Pareto-optimal" sub="badge and filter">
            <p>
              An entry carries the badge when <em>no other entry for the same molecule</em>{" "}
              is better on both accuracy and hardware cost at once.
            </p>
            <p>
              It marks a genuine trade-off. An entry without the badge is beaten on both
              axes by something else in the table, so there is no set of priorities under
              which it is the right choice for that molecule. Roughly half the suite is
              strictly dominated in this sense.
            </p>
          </Row>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">The three views</h2>

        <p>
          The tabs re-rank the same entries and show the columns relevant to each question:
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Accuracy</strong> — ranked by gap. Shows the classical baseline, so you
            can see the distance to CCSD(T).
          </li>
          <li>
            <strong>Cost</strong> — ranked by hardware cost. Shows gate counts, depth and
            T-gate estimates.
          </li>
          <li>
            <strong>Balanced</strong> — a combined score, and the only view that shows
            accuracy <em>and</em> cost on the same row. This is the view to use if you want
            to judge whether an approach is worth its resources.
          </li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-3">What these numbers do not tell you</h2>

        <p>Stated plainly, because each is easy to over-read:</p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>These are exact statevector simulations</strong>, not hardware runs.
            There is no gate noise, no readout error and no device topology. A circuit that
            reaches 2 mHa here would not reach 2 mHa on a real device today.
          </li>
          <li>
            <strong>The shot budget is not in the cost columns.</strong> Gate counts price
            one circuit execution; a real VQE run needs millions to hundreds of millions of
            executions, and how those are spent changes the answer substantially. That cost
            is measured separately in{" "}
            <Link href="/blog/shot-allocation-neyman-trap" className="text-primary hover:underline">
              our work on shot allocation
            </Link>.
          </li>
          <li>
            <strong>A small gap is not a chemical prediction.</strong> It means the
            algorithm solved <em>its own</em> problem well. Basis-set and active-space
            error sit on top and are usually much larger.
          </li>
          <li>
            <strong>Classical methods still win at these sizes.</strong> Nothing here is a
            claim of quantum advantage, and the CCSD(T) column is there so that is visible
            at a glance.
          </li>
        </ul>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm text-muted-foreground leading-6">
            Every entry records its full provenance — Hamiltonian, ansatz, optimiser, seed,
            package versions and code commit — so any number here can be rebuilt from
            scratch. See{" "}
            <Link href="/methodology" className="text-primary hover:underline">
              the methodology
            </Link>{" "}
            for how entries are produced and certified, or the{" "}
            <Link href="/leaderboard" className="text-primary hover:underline">
              leaderboard
            </Link>{" "}
            to read the numbers themselves.
          </p>
        </div>
      </div>
    </main>
  );
}
