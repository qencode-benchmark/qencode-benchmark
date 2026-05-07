import Link from "next/link";

export const metadata = {
  title: "H₂O Benchmarking: First 8-Qubit Results on the QEncode Leaderboard",
  description:
    "We added water to the QEncode benchmark suite. Here's what it takes to simulate H₂O with a [4,4] active space — 8 qubits, 185 Pauli terms, and what the VQE results reveal about UCCSD's limits.",
  alternates: { canonical: "/blog/h2o-first-8-qubit-benchmark" },
  openGraph: {
    title: "H₂O Benchmarking: First 8-Qubit Results on the QEncode Leaderboard",
    description:
      "Adding water to the quantum chemistry benchmark suite reveals the gap between UCCSD and hardware-efficient ansatz at 8 qubits.",
    url: "https://www.qencode-benchmark.org/blog/h2o-first-8-qubit-benchmark",
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
          <span>7 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          H₂O Benchmarking: First 8-Qubit Results on the QEncode Leaderboard
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          We added water to the QEncode benchmark suite. Here's what it takes to simulate H₂O
          with a [4,4] active space — 8 qubits, 105 Pauli terms, and what the VQE results reveal
          about UCCSD's limits at this scale.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <p>
          Water is arguably the most important molecule in chemistry. It is also a meaningful step
          up in complexity from the diatomics and triatomics that typically populate quantum
          chemistry benchmarks. Adding H₂O to the QEncode leaderboard meant moving from 4-qubit
          problems (H₂, LiH, HF) and the 8-qubit BeH₂ to a genuinely polyatomic molecule with
          lone pairs, two O–H bonds, and a more intricate correlation structure.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why [4,4] active space?</h2>

        <p>
          Full-valence H₂O in STO-3G has 10 electrons and 7 spatial orbitals. Running VQE on
          the full space would require 14 qubits — expensive and not yet the focus of our suite.
          Instead we freeze the oxygen 1s core and select a [4,4] active space: 4 electrons in
          4 orbitals (the two lone pairs and the two O–H bonding orbitals). This captures the
          dominant correlation effects while keeping the circuit to 8 qubits — the same as BeH₂.
        </p>

        <p>
          The exact FCI ground state energy within this active space is <strong>−6.163 Ha</strong>.
          The Hartree–Fock reference is −6.113 Ha, so the correlation energy we're trying to
          recover is about 50 mHa.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The Hamiltonian: 105 Pauli terms</h2>

        <p>
          After fermion-to-qubit mapping, the H₂O [4,4] Hamiltonian contains <strong>105 Pauli
          terms</strong> regardless of which mapping you use (Jordan-Wigner, parity, or
          Bravyi-Kitaev all produce the same term count at this active space size). For comparison,
          BeH₂ [4,4] also produces around 105 terms — confirming that term count is driven by the
          active space dimensions, not the specific molecule.
        </p>

        <p>
          More terms means each energy evaluation is more expensive: the VQE optimizer must
          contract a larger expectation value at every function call. With 1500–2000 COBYLA
          iterations per run and StatevectorEstimator handling the inner loop, each UCCSD entry
          takes approximately 7–10 minutes on a modern CPU.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">UCCSD results: three certified entries</h2>

        <p>
          We ran UCCSD (reps=1) under all three encodings. All three converged within the
          certification threshold (gap &lt; 10 mHa):
        </p>

        <div className="rounded-lg border overflow-hidden my-6">
          <table className="w-full text-sm">
            <thead className="bg-muted/40">
              <tr>
                <th className="text-left px-4 py-2.5 font-medium">Mapping</th>
                <th className="text-left px-4 py-2.5 font-medium">Ansatz</th>
                <th className="text-right px-4 py-2.5 font-medium">Gap (Ha)</th>
                <th className="text-right px-4 py-2.5 font-medium">Depth</th>
                <th className="text-right px-4 py-2.5 font-medium">2Q gates</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="px-4 py-2.5">Jordan-Wigner</td>
                <td className="px-4 py-2.5 font-mono text-xs">uccsd</td>
                <td className="px-4 py-2.5 text-right">3.54 × 10⁻³</td>
                <td className="px-4 py-2.5 text-right">2512</td>
                <td className="px-4 py-2.5 text-right">1440</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5">Parity</td>
                <td className="px-4 py-2.5 font-mono text-xs">uccsd</td>
                <td className="px-4 py-2.5 text-right">3.54 × 10⁻³</td>
                <td className="px-4 py-2.5 text-right">2426</td>
                <td className="px-4 py-2.5 text-right">1316</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5">Bravyi-Kitaev</td>
                <td className="px-4 py-2.5 font-mono text-xs">uccsd</td>
                <td className="px-4 py-2.5 text-right">3.55 × 10⁻³</td>
                <td className="px-4 py-2.5 text-right">2458</td>
                <td className="px-4 py-2.5 text-right">1316</td>
              </tr>
              <tr>
                <td className="px-4 py-2.5">Jordan-Wigner</td>
                <td className="px-4 py-2.5 font-mono text-xs">hea</td>
                <td className="px-4 py-2.5 text-right">7.45 × 10⁻³</td>
                <td className="px-4 py-2.5 text-right">27</td>
                <td className="px-4 py-2.5 text-right">56</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p>
          All three UCCSD encodings converge to nearly the same gap (~3.54 mHa). The parity
          mapping produces the shallowest circuit (depth 2426 vs 2512 for JW), and BK matches
          parity on two-qubit gate count. If you're hardware-constrained, parity is the clear
          winner for UCCSD on H₂O.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Hardware-efficient ansatz: a split result</h2>

        <p>
          We ran hardware-efficient ansatz (HEA, reps=2) under all three mappings. Only the
          Jordan-Wigner encoding converged within the certification threshold (gap 7.45 mHa).
          The Bravyi-Kitaev and parity HEA runs produced gaps of 0.38 Ha and 0.37 Ha respectively —
          about 100× worse than UCCSD.
        </p>

        <p>
          This is not a bug. HEA with reps=2 has 48 free parameters but no built-in particle
          conservation or chemistry-informed structure. On a molecule with this many Pauli terms and
          a moderately deep energy landscape, COBYLA with 1500 iterations frequently gets stuck in a
          local minimum. The JW encoding happened to land in the right basin with our random seed;
          BK and parity did not.
        </p>

        <p>
          This reveals an important point: HEA's performance is encoding-sensitive in ways that
          UCCSD is not. UCCSD carries the physics of the system into the ansatz structure — it knows
          about electron pairs and excitations. HEA is agnostic, which makes it cheaper to compile
          but harder to converge reliably.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">How H₂O compares to the rest of the suite</h2>

        <p>
          The H₂O UCCSD gap (~3.5 mHa) is roughly the same as BeH₂ UCCSD (~3.6 mHa). This makes
          sense: both use a [4,4] active space with 8 qubits. The correlation energy per active
          electron is similar because we're choosing the same active space size even though the
          molecules are different. What differs is the circuit depth: H₂O UCCSD runs ~2500 deep vs
          BeH₂'s ~1750. H₂O has more off-diagonal Pauli terms that require longer sequences of
          Givens rotations in the UCCSD construction.
        </p>

        <p>
          By contrast, H₂ and HF achieve gaps in the nanoHartree range — essentially machine
          precision. That's because their [2,2] active spaces are tiny (4 qubits), and UCCSD with
          just a few parameters finds the exact ground state within the active space almost
          immediately. H₂O at [4,4] is a genuinely harder optimization problem.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What comes next for H₂O</h2>

        <p>
          The 3.5 mHa gap is certified but sits above the chemical accuracy threshold of 1.6 mHa
          (1 kcal/mol). To close that gap we plan to:
        </p>

        <ul className="list-disc pl-6 space-y-1">
          <li>Run with more optimizer restarts (currently 1, trying 3–5) to escape local minima</li>
          <li>Increase COBYLA iterations from 2000 to 4000–5000</li>
          <li>Benchmark k-UpCCGSD, which adds higher-order excitations at moderate extra cost</li>
        </ul>

        <p>
          H₂O is now live on the{" "}
          <Link href="/leaderboard" className="text-primary hover:underline">
            QEncode leaderboard
          </Link>{" "}
          under the Best Accuracy, Lowest Cost, and Balanced categories. Filter to H₂O to see
          the full breakdown by encoding and ansatz.
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
