import Link from "next/link";

export const metadata = {
  title: "ADAPT-VQE Certifies Benzene — How We Broke the Medium Molecule Barrier",
  description:
    "COBYLA and UCCSD hit a wall at ~400 parameters. ADAPT-VQE breaks it by building the ansatz adaptively. We used it to certify H₆ (28 operators) and benzene (10 operators) — the first aromatic molecule certified on QEncode.",
  alternates: { canonical: "/blog/adapt-vqe-certifies-benzene" },
  openGraph: {
    title: "ADAPT-VQE Certifies Benzene — How We Broke the Medium Molecule Barrier",
    description:
      "ADAPT-VQE selects only the operators that matter. Result: benzene certified at 9.976 mHa with 10 operators instead of 400. First aromatic molecule certified on QEncode.",
    url: "https://www.qencode-benchmark.org/blog/adapt-vqe-certifies-benzene",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "ADAPT-VQE Certifies Benzene — How We Broke the Medium Molecule Barrier",
  description:
    "COBYLA and UCCSD hit a wall at ~400 parameters. ADAPT-VQE breaks it by building the ansatz adaptively. We used it to certify H₆ and benzene — the first aromatic molecule certified on QEncode.",
  datePublished: "2026-05-29",
  dateModified: "2026-05-29",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/adapt-vqe-certifies-benzene",
  keywords: [
    "ADAPT-VQE", "benzene VQE", "quantum chemistry benchmark", "CASSCF",
    "medium molecules", "H6 hydrogen chain", "QEncode v4.3", "variational quantum eigensolver",
    "COBYLA optimization", "aromatic molecule quantum computing",
  ],
};

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-05-29">May 29, 2026</time>
          <span>·</span>
          <span>9 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          ADAPT-VQE Certifies Benzene — How We Broke the Medium Molecule Barrier
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          For months, molecules beyond six heavy atoms were out of reach. UCCSD with a gradient-free
          optimizer generates hundreds of parameters and simply never converges. ADAPT-VQE changes
          the equation: it builds the ansatz one operator at a time, selecting only the ones that
          actually matter. The result — H₆ certified at 9.755 mHa, benzene certified at 9.976 mHa.
          The first aromatic molecule on the QEncode leaderboard.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <h2 className="text-xl font-semibold mt-8 mb-3">The wall we kept hitting</h2>

        <p>
          After certifying N₂ in Suite v4.1, the logical next targets were the medium molecules:
          H₆, H₈, benzene, small drug fragments. All of them share the same active space structure
          — roughly [6e, 6o], twelve qubits in the Jordan-Wigner encoding, nine after Z2 tapering.
          On paper, this is the same size as the N₂ calculation that already worked.
        </p>

        <p>
          In practice, something else happened. Every run on H₆ and benzene with UCCSD ran for
          hours — sometimes overnight — with no checkpoint, no convergence, and no meaningful
          decrease in energy. Killing the process and inspecting the logs showed a familiar
          pattern: the optimizer was evaluating the circuit thousands of times but wandering
          through parameter space without direction.
        </p>

        <p>
          N₂ UCCSD worked, just barely, for a specific reason: the D∞h symmetry of the nitrogen
          molecule and a lucky initialization at the Hartree-Fock reference (all-zero parameters)
          put COBYLA near a shallow basin. H₆, with its lower linear-chain symmetry, and benzene,
          with its large π conjugation, have no such shortcut.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why COBYLA breaks at scale</h2>

        <p>
          COBYLA — Constrained Optimization BY Linear Approximations — is a gradient-free optimizer
          that builds a local linear model of the function at each step. It needs roughly 2N function
          evaluations per iteration to maintain that model, where N is the number of parameters. For
          UCCSD on a [6e, 6o] active space, N is around 400.
        </p>

        <p>
          That means each COBYLA iteration requires approximately 800 circuit evaluations — and
          reaching anything close to convergence takes thousands of iterations. On a 9-qubit
          statevector simulator evaluating a 914-term Hamiltonian, this is simply not practical.
          Published benchmarks confirm this is not a local issue: COBYLA requires 23× more runtime
          than gradient-based methods for comparable accuracy, and for large parameter counts it
          often fails entirely.
        </p>

        <p>
          This is an industry-wide finding, not a QEncode bug. The lesson: COBYLA is excellent for
          small circuits (up to ~40 parameters) and becomes infeasible above ~200.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">ADAPT-VQE: build only what you need</h2>

        <p>
          ADAPT-VQE (Adaptive Derivative-Assembled Pseudo-Trotter ansatz Variational Quantum
          Eigensolver) was proposed by Grimsley et al. in 2019 as a direct response to the
          parameter scaling problem. The core idea is simple: instead of building the full UCCSD
          ansatz upfront and optimizing all parameters simultaneously, build it one operator at
          a time.
        </p>

        <p>
          Each iteration:
        </p>

        <ol className="list-decimal pl-6 space-y-2">
          <li>Compute the gradient of the energy with respect to adding each operator in the pool at parameter zero — using the exact parameter-shift rule, not finite differences.</li>
          <li>Select the operator with the largest absolute gradient. This is the operator that, right now, would reduce the energy most.</li>
          <li>Append it to the circuit with a new parameter initialized to zero.</li>
          <li>Re-optimize all current parameters with COBYLA until convergence.</li>
          <li>Repeat until the largest gradient falls below a threshold or the certification gap is met.</li>
        </ol>

        <p>
          The operator pool is identical to the full UCCSD pool — no operators are pre-excluded.
          The difference is that ADAPT selects a small, problem-specific subset. For a [6e, 6o]
          active space with 424 possible UCCSD operators, ADAPT typically selects 10–30 to reach
          chemical accuracy. Each COBYLA sub-problem has only as many parameters as operators
          selected so far — starting at 1, growing slowly.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">H₆: first medium molecule certified</h2>

        <p>
          The first ADAPT-VQE run on a medium molecule was H₆ — a six-hydrogen linear chain at
          1.0 Å spacing, [6e, 6o] active space, CASSCF orbital optimization, Jordan-Wigner
          encoding, 9 qubits after tapering.
        </p>

        <div className="bg-muted/40 border rounded-lg p-5 my-6 font-mono text-sm space-y-1">
          <div className="flex justify-between"><span className="text-muted-foreground">Operator pool size</span><span>424</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Operators selected</span><span>28</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Parameters optimized</span><span>28</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">vs UCCSD params</span><span>424 (15× fewer)</span></div>
          <div className="flex justify-between border-t pt-2 mt-2"><span className="text-muted-foreground">Gap |VQE − CASCI|</span><span className="text-green-600 dark:text-green-400 font-semibold">9.755 mHa — CERTIFIED</span></div>
        </div>

        <p>
          The same calculation with COBYLA + UCCSD ran for over eight hours with no checkpoint —
          not a slow convergence, but no convergence at all. ADAPT-VQE reached certification with
          28 operators. The energy decreased monotonically with each added operator, and the
          gradient norm decreased monotonically as well — exactly what the theory predicts.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Benzene: first aromatic molecule certified</h2>

        <p>
          Benzene is the canonical aromatic molecule — a six-carbon ring with six π electrons
          delocalized across the ring. In quantum chemistry, it is the simplest example of a
          conjugated π system, and its electron correlation structure is fundamentally different
          from the molecules certified in earlier suites.
        </p>

        <p>
          The active space [6e, 6o] captures the full π manifold: three bonding π orbitals and
          three antibonding π* orbitals. After CASSCF orbital optimization and Jordan-Wigner
          encoding, this maps to 12 qubits and a Hamiltonian with 914 Pauli terms — the largest
          Hamiltonian in the QEncode suite to date.
        </p>

        <div className="bg-muted/40 border rounded-lg p-5 my-6 font-mono text-sm space-y-1">
          <div className="flex justify-between"><span className="text-muted-foreground">CASCI (target)</span><span>−230.787137 Ha</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">VQE best energy</span><span>−230.777161 Ha</span></div>
          <div className="flex justify-between border-t pt-2 mt-2"><span className="text-muted-foreground">Gap |VQE − CASCI|</span><span className="text-green-600 dark:text-green-400 font-semibold">9.976 mHa — CERTIFIED</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Operators selected</span><span>10 / pool of 424</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Circuit evaluations</span><span>801</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Backend</span><span>lightning.qubit (C++)</span></div>
        </div>

        <p>
          Benzene certified with just 10 operators — fewer than H₆ despite being a larger molecule.
          This is not surprising in retrospect. Benzene's D6h symmetry, the highest of any molecule
          in the suite, means the most impactful excitation operators are immediately obvious to the
          gradient selector. The π system is perfectly symmetric, so a small number of operators
          captures the dominant correlation. ADAPT exploits this directly; UCCSD cannot.
        </p>

        <p>
          The benchmark ran on a local machine using the{" "}
          <code className="text-sm bg-muted px-1 py-0.5 rounded">lightning.qubit</code> C++ backend
          — the same hardware that benzene UCCSD crashed twice (black screen, 7+ hours of compute
          lost). With ADAPT and lightning.qubit, the same certification finished in minutes.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What the operator count tells you</h2>

        <p>
          The number of ADAPT operators selected is a physically meaningful quantity. It reflects
          how many distinct electronic excitation channels are needed to describe the ground state
          to within the certification threshold. Small counts indicate a high-symmetry, structured
          correlation problem. Large counts indicate a molecule where many excitations contribute
          roughly equally — harder for any method.
        </p>

        <p>
          For the QEncode leaderboard, ADAPT entries display the operator count alongside the
          standard gap and qubit count. This gives a direct comparison: a certified benzene entry
          with 10 ADAPT operators versus a hypothetical hardware-efficient entry needing 63
          parameters but unable to certify — the ADAPT entry is both more accurate and more
          interpretable.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The correctness question</h2>

        <p>
          We want to be explicit about what ADAPT-VQE is and is not doing, because "10 operators
          certified benzene" sounds like it should not work.
        </p>

        <p>
          The operator pool is the complete UCCSD pool — every symmetry-allowed single and double
          excitation after tapering. No operators are pre-selected or pre-excluded based on
          knowledge of the answer. The gradient computation uses PennyLane's exact parameter-shift
          rule, not finite differences or approximations. The energy evaluation is a full
          statevector inner product against the complete 914-term Hamiltonian. The CASCI reference
          is computed independently by PySCF before any VQE runs.
        </p>

        <p>
          The certification criterion is the same as for every other entry: the absolute gap
          between the VQE energy and the CASCI ground state energy, computed from first principles,
          must be below 10 mHa. There is no parameter tuning, no post-hoc correction, no selection
          of favorable runs. The gap for benzene is 9.976 mHa. It certifies.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What this unlocks</h2>

        <p>
          ADAPT-VQE is now the default approach for any molecule where UCCSD parameter counts
          exceed roughly 100. This covers most of the molecules we want to benchmark next: longer
          hydrogen chains (H₈, H₁₀), formaldehyde, butadiene, and eventually drug-relevant
          fragments like pyridine and glycine.
        </p>

        <p>
          The existing 32 certified entries are unchanged — ADAPT is an additive capability, not
          a replacement. Entries generated with UCCSD remain in the leaderboard with their ansatz
          type clearly labeled. ADAPT entries appear alongside them with the operator count
          displayed as an additional quality metric.
        </p>

        <p>
          For fault-tolerant resource estimation (planned for v4.4), ADAPT entries are especially
          valuable: the T-gate count for a fault-tolerant implementation scales with the operator
          count, not the full UCCSD pool. Ten operators instead of 400 represents a 40× reduction
          in T-gate depth for benzene — the kind of number that matters when estimating timelines
          for practical quantum advantage.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Running it yourself</h2>

        <p>
          All ADAPT-VQE entries are fully reproducible. The{" "}
          <code className="text-sm bg-muted px-1 py-0.5 rounded">--ansatz-type adapt</code> flag
          is available in the Suite v4.3 generator:
        </p>

        <pre className="bg-muted rounded-md p-4 text-sm font-mono overflow-x-auto">
{`python scripts/generate_entry_v4.py \\
  --molecule benzene \\
  --mapping jordan_wigner \\
  --ansatz-type adapt \\
  --orbital-opt casscf \\
  --backend lightning.qubit \\
  --out-dir releases/v4/db`}
        </pre>

        <p>
          The entry JSON includes the full operator pool size, the list of selected operator
          indices, the gradient threshold used, and whether the ADAPT loop converged on the
          gradient criterion or stopped via the energy early-stop. Every number is traceable.
        </p>

        <div className="mt-10 border-t pt-8 flex flex-col sm:flex-row gap-3">
          <Link
            href="/leaderboard"
            className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            View benzene on the leaderboard →
          </Link>
          <Link
            href="https://github.com/qencode-benchmark/qencode-benchmark"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            GitHub repository
          </Link>
        </div>

      </div>
    </main>
  );
}
