import Link from "next/link";

export const metadata = {
  title: "Jordan-Wigner vs Parity vs Bravyi-Kitaev: A Practical Comparison for VQE",
  description:
    "A technical comparison of the three main fermionic-to-qubit encodings — Jordan-Wigner, parity, and Bravyi-Kitaev — with benchmark data showing how encoding choice affects VQE circuit depth, gate count, and energy accuracy.",
  alternates: { canonical: "/blog/jordan-wigner-vs-parity-vs-bravyi-kitaev" },
  openGraph: {
    title: "Jordan-Wigner vs Parity vs Bravyi-Kitaev: A Practical Comparison for VQE",
    description:
      "How does your choice of qubit encoding affect VQE performance? We compare JW, parity, and BK encodings across five molecules with real benchmark data.",
    url: "https://www.qencode-benchmark.org/blog/jordan-wigner-vs-parity-vs-bravyi-kitaev",
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
          <time dateTime="2026-04-25">April 25, 2026</time>
          <span>·</span>
          <span>9 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          Jordan-Wigner vs Parity vs Bravyi-Kitaev: A Practical Comparison for VQE
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Before you run a single VQE circuit, you have to answer a question that most tutorials
          skip: which qubit encoding should you use? We compared all three standard encodings
          across five molecules with real benchmark data. Here's what actually matters.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <p>
          The Variational Quantum Eigensolver operates on qubits, but molecular Hamiltonians are
          written in terms of fermionic operators — creation and annihilation operators that obey
          anti-commutation relations. To run VQE, you need a mapping that converts fermionic
          operators into qubit operators. This mapping is called a qubit encoding.
        </p>

        <p>
          Three encodings dominate the literature: <strong>Jordan-Wigner (JW)</strong>,{" "}
          <strong>parity</strong>, and <strong>Bravyi-Kitaev (BK)</strong>. All three are
          mathematically exact — they preserve the fermionic anti-commutation relations and
          produce identical ground-state energies in the limit of perfect optimization. But they
          differ significantly in how they distribute information across qubits, which has
          direct consequences for circuit depth, gate count, and practical VQE performance.
        </p>

        <p>
          QEncode Suite v2 benchmarks every molecule-ansatz combination at all three encodings.
          Here's what the data shows.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">How each encoding works</h2>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">Jordan-Wigner</h3>
        <p>
          Jordan-Wigner is the oldest and most intuitive encoding. Each qubit directly
          represents one spin-orbital: qubit <em>k</em> stores whether spin-orbital <em>k</em> is
          occupied (|1⟩) or empty (|0⟩). Fermionic creation and annihilation operators are
          mapped to Pauli strings where the anti-commutation relations are enforced by a chain
          of Z operators extending from qubit 0 to qubit <em>k−1</em>.
        </p>
        <p>
          The consequence is locality: JW operators can be long. A fermionic operator acting on
          spin-orbital <em>k</em> becomes a Pauli string of length <em>k</em>, because all
          qubits below <em>k</em> must be included to enforce the correct fermionic statistics.
          For a molecule with many spin-orbitals, this produces deep, gate-heavy circuits.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">Parity encoding</h3>
        <p>
          Parity encoding reorganizes what each qubit stores. Instead of occupation numbers,
          each qubit stores the <em>parity</em> of all spin-orbitals up to that index — whether
          an even or odd number of them are occupied. This makes fermionic operators more local:
          a creation or annihilation operator acting on spin-orbital <em>k</em> only requires
          qubits <em>k</em> and <em>k+1</em>, regardless of how many spin-orbitals are below it.
        </p>
        <p>
          The practical benefit of parity encoding is a two-qubit reduction. Because the total
          particle number and total spin are conserved quantities, two qubits in the parity
          basis become redundant and can be removed. For a molecule that requires <em>n</em>{" "}
          qubits under JW, parity encoding uses <em>n−2</em> qubits. This directly reduces
          circuit depth and gate count, since the excitation operators in UCCSD scale with qubit
          count.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">Bravyi-Kitaev</h3>
        <p>
          Bravyi-Kitaev is a more sophisticated encoding that stores information in a balanced
          binary tree structure. Each qubit encodes a combination of occupation and parity
          information over a range of spin-orbitals whose size scales logarithmically with
          system size. This gives BK operators that scale as O(log n) rather than O(n) for JW
          or O(1)/O(2) for parity.
        </p>
        <p>
          BK is theoretically appealing for large systems where the logarithmic scaling becomes
          meaningful. In practice, for the 4–14 qubit systems in QEncode Suite v2, the
          difference is smaller than the theory suggests because the constant factors matter at
          small system sizes.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">What the benchmark data shows</h2>

        <p>
          Across all five Suite v2 molecules and both ansatz families, three consistent patterns
          emerge from the benchmark data.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">Pattern 1: Parity wins on circuit cost for UCCSD</h3>
        <p>
          For UCCSD, parity encoding consistently produces the shallowest circuits and lowest
          two-qubit gate counts. The two-qubit reduction compounds through the ansatz
          construction: fewer qubits means fewer excitation operators, which means fewer
          parameterized gates. For BeH₂ — the largest Suite v2 molecule at 14 qubits under JW
          — parity encoding reduces the two-qubit gate count by 18–24% compared to JW, and
          produces circuits 15–20% shallower.
        </p>
        <p>
          This makes parity the default encoding recommendation for UCCSD on any of the Suite
          v2 molecules.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">Pattern 2: JW and parity tie on accuracy</h3>
        <p>
          Despite the circuit depth advantage of parity, the energy gap results are
          statistically indistinguishable between JW and parity across all molecules. Both
          encodings reach chemical accuracy with UCCSD on H₂, LiH, and HF. Both struggle
          equally with N₂ under noisy conditions. The encoding doesn't affect the expressibility
          of the ansatz in the noiseless simulation setting — all three encodings reach the same
          FCI energy given sufficient optimization.
        </p>
        <p>
          This means the accuracy leaderboard is encoding-neutral: a UCCSD result at parity
          encoding and a UCCSD result at JW encoding that both achieve chemical accuracy are
          equivalent scientifically. The difference only shows up in the cost and balanced
          categories.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">Pattern 3: BK underperforms at small qubit counts</h3>
        <p>
          Bravyi-Kitaev's theoretical advantage is logarithmic scaling — meaningful when you
          have 50+ qubits. In the 4–14 qubit range of Suite v2, the overhead from the binary
          tree structure's non-local indexing pattern produces circuits that are consistently
          slightly deeper than parity and comparable to or slightly worse than JW.
        </p>
        <p>
          For H₂ (4 qubits) and LiH (12 qubits), BK circuits have 5–12% more two-qubit gates
          than the parity equivalents. For N₂ and BeH₂, the gap is smaller but parity still
          comes out ahead. BK holds a theoretical advantage for future large-molecule benchmarks
          where qubit counts exceed 30–40, but it's not the practical choice for current Suite
          v2 molecules.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">Encoding and hardware-efficient ansatz</h2>
        <p>
          The encoding choice matters much less for hardware-efficient ansatz than for UCCSD.
          HEA doesn't use the fermionic structure of the problem — it just places parameterized
          gates across the qubit register. The qubit reduction from parity encoding still
          applies (fewer qubits = shallower HEA circuit), but the effect is proportionally
          smaller because HEA circuits are already shallower and the ansatz structure doesn't
          amplify the qubit count difference the way UCCSD does.
        </p>
        <p>
          For HEA on H₂ and LiH, JW and parity produce circuits that differ by only 1–2
          two-qubit gates. For practical purposes, encoding choice is a secondary concern when
          using HEA on small molecules.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">A note on Hamiltonian term count</h2>
        <p>
          One metric we track internally but don't surface on the leaderboard is the number of
          Pauli terms in the qubit Hamiltonian after encoding. This matters for shot-based
          (non-statevector) evaluation because each distinct Pauli term typically requires a
          separate measurement circuit.
        </p>
        <p>
          Under JW, the Hamiltonian term count is generally higher than under parity or BK for
          the same molecule. For LiH under JW, the full qubit Hamiltonian has over 600 Pauli
          terms; under parity with two-qubit reduction, this drops below 450. For teams
          planning real hardware runs — where shot budget is a genuine constraint — this
          difference in Hamiltonian term count becomes significant and favors parity encoding
          more strongly than the noiseless simulation results suggest.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">Practical recommendations</h2>

        <p>
          Based on the Suite v2 benchmark data:
        </p>

        <ul className="list-disc pl-6 space-y-3">
          <li>
            <strong>For UCCSD on any Suite v2 molecule:</strong> use parity encoding. The
            two-qubit reduction produces measurably shallower circuits with no accuracy penalty.
            It's the right default.
          </li>
          <li>
            <strong>For HEA on small molecules (H₂, LiH):</strong> encoding choice is minor.
            Use parity for consistency, but JW is equally acceptable.
          </li>
          <li>
            <strong>For real hardware runs with shot budgets:</strong> parity encoding's lower
            Hamiltonian term count provides an additional practical advantage beyond circuit
            depth.
          </li>
          <li>
            <strong>For research comparing encodings:</strong> the QEncode leaderboard provides
            matched results across all three encodings under identical conditions — the only
            publicly available standardized comparison of this kind.
          </li>
          <li>
            <strong>For future large-molecule work (30+ qubits):</strong> revisit BK. Its
            logarithmic scaling becomes material at qubit counts the current Suite v2 doesn't
            reach.
          </li>
        </ul>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">Why encoding choice is underreported</h2>
        <p>
          Most VQE papers fix one encoding and don't discuss the choice. Jordan-Wigner is the
          most common default — it's conceptually simplest and most tutorials use it — which
          means a significant fraction of published results leave circuit depth optimization on
          the table. Switching from JW to parity encoding is a one-line change in Qiskit
          (replace <code className="text-xs bg-muted px-1.5 py-0.5 rounded">JordanWignerMapper</code> with{" "}
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded">ParityMapper</code>) and
          consistently produces shallower circuits for UCCSD.
        </p>
        <p>
          The QEncode leaderboard benchmarks all three encodings for every certified submission,
          so the encoding effect is always visible in the results. If your submission uses JW
          and a competitor uses parity, the cost leaderboard will show the difference directly.
        </p>

        <div className="mt-10 p-5 rounded-lg border bg-muted/40">
          <p className="text-sm font-medium text-foreground mb-2">See encoding comparisons on the live leaderboard</p>
          <p className="text-sm text-muted-foreground mb-4">
            Every certified QEncode result includes results at Jordan-Wigner, parity, and
            Bravyi-Kitaev encoding. The leaderboard lets you filter by molecule, encoding, and
            ansatz to see the comparisons directly.
          </p>
          <div className="flex gap-3 flex-wrap">
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
            <Link
              href="/pricing"
              className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
            >
              Submit for certification
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-14 pt-8 border-t flex items-center justify-between text-sm">
        <Link href="/blog" className="text-muted-foreground hover:text-foreground transition-colors">
          ← All posts
        </Link>
        <Link href="/blog/uccsd-vs-hardware-efficient-ansatz" className="text-muted-foreground hover:text-foreground transition-colors">
          Next: UCCSD vs HEA →
        </Link>
      </div>
    </main>
  );
}
