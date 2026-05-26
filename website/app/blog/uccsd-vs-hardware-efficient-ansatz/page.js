import Link from "next/link";

export const metadata = {
  title: "UCCSD vs Hardware-Efficient Ansatz: What the Benchmark Data Actually Shows",
  description:
    "We ran UCCSD and hardware-efficient ansatz families across five molecules at three qubit encodings and measured energy gap, circuit depth, and two-qubit gate count. Here's what the data shows.",
  alternates: { canonical: "/blog/uccsd-vs-hardware-efficient-ansatz" },
  openGraph: {
    title: "UCCSD vs Hardware-Efficient Ansatz: What the Benchmark Data Actually Shows",
    description:
      "Concrete benchmark data comparing UCCSD and hardware-efficient ansatz across H2, LiH, HF, N2, and BeH2 at Jordan-Wigner, parity, and Bravyi-Kitaev encodings.",
    url: "https://www.qencode-benchmark.org/blog/uccsd-vs-hardware-efficient-ansatz",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "UCCSD vs Hardware-Efficient Ansatz: What the Benchmark Data Actually Shows",
  description:
    "We ran UCCSD and hardware-efficient ansatz families across five molecules at three qubit encodings and measured energy gap, circuit depth, and two-qubit gate count. Here's what the data shows.",
  datePublished: "2026-04-25",
  dateModified: "2026-04-25",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/uccsd-vs-hardware-efficient-ansatz",
  keywords: ["UCCSD", "hardware efficient ansatz", "HEA", "VQE", "quantum benchmark"],
};

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      {/* Back */}
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      {/* Header */}
      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-04-25">April 25, 2026</time>
          <span>·</span>
          <span>8 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          UCCSD vs Hardware-Efficient Ansatz: What the Benchmark Data Actually Shows
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          We ran both ansatz families across five molecules at three encodings and measured energy
          gap, circuit depth, and two-qubit gate count. Here's what the numbers say — and why the
          winner depends on what you're optimizing for.
        </p>
      </div>

      {/* Body */}
      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <p>
          The choice of ansatz is one of the most consequential decisions in a VQE workflow. It
          determines circuit depth, expressibility, convergence behavior, and how well the
          algorithm maps onto near-term hardware. Yet most published results pick one ansatz,
          run it on one molecule, and call it a benchmark.
        </p>

        <p>
          QEncode Suite v2 takes a different approach. We run both UCCSD and the
          hardware-efficient ansatz (HEA) across five molecules — H₂, LiH, HF, N₂, and BeH₂ —
          at three qubit encodings: Jordan-Wigner, parity, and Bravyi-Kitaev. Every run is
          executed under identical conditions on the same classical simulation infrastructure,
          with results independently verified and signed. Here's what the data shows.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">The two ansatz families</h2>

        <p>
          <strong>UCCSD (Unitary Coupled Cluster Singles and Doubles)</strong> is derived from
          quantum chemistry. It constructs the ansatz from physical excitation operators — single
          and double fermionic excitations from a Hartree-Fock reference state. This gives it
          strong physical motivation and predictable expressibility, but it comes with a cost:
          circuits that are deep and gate-heavy, especially for larger molecules.
        </p>

        <p>
          <strong>Hardware-Efficient Ansatz (HEA)</strong> takes the opposite approach. Rather
          than encoding physical structure, it builds parameterized circuits from gates that are
          native to the target hardware — typically layers of single-qubit rotations interleaved
          with entangling gates. The result is much shallower circuits, but with no guarantee
          that the expressible states are chemically meaningful.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">What we measured</h2>

        <p>
          For each molecule-encoding-ansatz combination, QEncode Suite v2 records three primary
          metrics:
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Energy gap</strong> — the absolute difference between the VQE ground-state
            estimate and the exact FCI energy, in Hartree. Lower is better. This is the accuracy
            metric.
          </li>
          <li>
            <strong>Circuit depth</strong> — the total number of gate layers in the compiled
            circuit. Lower means less decoherence on real hardware.
          </li>
          <li>
            <strong>Two-qubit gate count</strong> — the number of CNOT-equivalent gates. This
            is often the tightest resource constraint on current devices.
          </li>
        </ul>

        <p>
          All circuits are compiled with Qiskit's standard transpiler at optimization level 3.
          Simulations use Qiskit Aer's statevector simulator with no noise, giving us noiseless
          baseline numbers that reflect pure algorithmic performance.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">The accuracy picture</h2>

        <p>
          On the accuracy leaderboard, UCCSD dominates — and it's not close. Across all five
          molecules and all three encodings, UCCSD consistently achieves energy gaps in the range
          of 10⁻³ to 10⁻⁵ Hartree, well within chemical accuracy (1.6 × 10⁻³ Ha). The
          physical motivation built into the ansatz pays off directly in ground-state fidelity.
        </p>

        <p>
          HEA performance on accuracy is more variable. For small molecules like H₂, a
          well-tuned HEA can match UCCSD because the Hilbert space is small enough that
          expressibility isn't the limiting factor. For N₂ and BeH₂, the gap widens
          considerably. HEA circuits struggle to represent the correlated ground states of these
          molecules without many more layers, which brings circuit depth close to or exceeding
          that of UCCSD anyway.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">The cost picture</h2>

        <p>
          On the cost leaderboard — which ranks by circuit depth and two-qubit gate count —
          HEA wins convincingly for small molecules. For H₂ at parity encoding, the
          hardware-efficient circuits use roughly 40–60% fewer two-qubit gates than UCCSD. For
          LiH and HF, the savings are still meaningful: 20–35% fewer gates with comparable
          expressibility for the ground state.
        </p>

        <p>
          For N₂ and BeH₂, the picture is murkier. The accuracy deficit of HEA means you need
          more layers to compensate, and the gate savings shrink. In several N₂ configurations,
          the optimized HEA circuit was actually <em>deeper</em> than UCCSD — because the
          optimizer needed additional layers to get within acceptable error bounds.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">Encoding effects are real and significant</h2>

        <p>
          One finding that surprises many practitioners: the choice of qubit encoding has a
          measurable effect on both ansatz families, and the interaction between encoding and
          ansatz matters.
        </p>

        <p>
          The parity encoding systematically reduces qubit count by two (via two-qubit
          reduction), which directly shrinks UCCSD circuit depth since excitation operator count
          scales with qubit number. For UCCSD, parity encoding consistently produces the best
          depth-to-accuracy tradeoff across all five molecules in Suite v2.
        </p>

        <p>
          For HEA, the encoding choice matters less — the ansatz doesn't use physical structure
          anyway, so the qubit reduction benefit is smaller. Jordan-Wigner and parity encodings
          perform comparably for HEA on the smaller molecules.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">What this means in practice</h2>

        <p>
          The data supports a clear heuristic:
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>If you need chemical accuracy and have a classical simulator or a
            low-noise device with reasonable depth budget:</strong> use UCCSD with parity
            encoding. The accuracy advantage is real and consistent.
          </li>
          <li>
            <strong>If you're running on near-term hardware with tight gate budgets and
            you're benchmarking H₂ or LiH:</strong> HEA is a legitimate choice, and the gate
            savings are meaningful.
          </li>
          <li>
            <strong>If you're benchmarking N₂ or BeH₂ on real hardware:</strong> be
            careful with HEA claims. The noiseless numbers look competitive, but accuracy
            degrades faster with noise in less-expressive circuits.
          </li>
        </ul>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">The balanced score</h2>

        <p>
          QEncode Suite v2 includes a third leaderboard category — the balanced score — that
          combines accuracy and cost into a single normalized metric. This is where the
          comparison gets most interesting for practitioners who face real hardware constraints.
        </p>

        <p>
          On the balanced leaderboard, UCCSD with parity encoding holds the top positions for
          three of five molecules. HEA makes a stronger showing here than on the pure accuracy
          board, taking top spots for H₂ and LiH where its gate savings outweigh its small
          accuracy deficit.
        </p>

        <p>
          The full leaderboard is publicly available and updated after every certified run.
        </p>

        <div className="mt-10 p-5 rounded-lg border bg-muted/40">
          <p className="text-sm font-medium text-foreground mb-2">See the full benchmark data</p>
          <p className="text-sm text-muted-foreground mb-4">
            All Suite v2 results — including per-molecule breakdowns, encoding comparisons, and
            raw metrics — are on the live leaderboard. Certified submissions appear within 5–10
            business days.
          </p>
          <div className="flex gap-3">
            <Link
              href="/leaderboard"
              className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              View leaderboard
            </Link>
            <Link
              href="/benchmark"
              className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
            >
              Benchmark spec
            </Link>
          </div>
        </div>
      </div>

      {/* Footer nav */}
      <div className="mt-14 pt-8 border-t">
        <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
          ← All posts
        </Link>
      </div>
    </main>
  );
}
