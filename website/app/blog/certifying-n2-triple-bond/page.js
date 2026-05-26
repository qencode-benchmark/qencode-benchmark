import Link from "next/link";

export const metadata = {
  title: "Certifying N₂: QEncode Benchmarks the Triple Bond",
  description:
    "N₂ is one of the hardest molecules in quantum chemistry — a triple bond with strong multireference character. Here's how we certified it at cc-pVDZ with CASSCF orbitals, 12 qubits, and a 2 mHa gap.",
  alternates: { canonical: "/blog/certifying-n2-triple-bond" },
  openGraph: {
    title: "Certifying N₂: QEncode Benchmarks the Triple Bond",
    description:
      "How QEncode certified nitrogen — 12 qubits, CASSCF orbital optimization, 404 UCCSD parameters, and a 2 mHa gap on one of quantum chemistry's hardest benchmarks.",
    url: "https://www.qencode-benchmark.org/blog/certifying-n2-triple-bond",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "Certifying N₂: QEncode Benchmarks the Triple Bond",
  description:
    "N₂ is one of the hardest molecules in quantum chemistry — a triple bond with strong multireference character. How we certified it at cc-pVDZ with CASSCF orbitals, 12 qubits, and a 2 mHa gap.",
  datePublished: "2026-05-21",
  dateModified: "2026-05-21",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/certifying-n2-triple-bond",
  keywords: ["N2 VQE", "CASSCF", "quantum benchmark", "DARPA QB-GSEE", "12 qubit", "UCCSD"],
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
          <time dateTime="2026-05-21">May 21, 2026</time>
          <span>·</span>
          <span>8 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          Certifying N₂: QEncode Benchmarks the Triple Bond
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Nitrogen is one of the canonical hard problems in quantum chemistry. A triple bond, strong
          multireference character, and a π orbital manifold that defeats standard Hartree-Fock
          partitioning. Here is how we certified it — 12 qubits, CASSCF orbital optimization, and
          a final gap of 2.0 mHa against the CASCI reference.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <p>
          Every quantum chemistry benchmark suite eventually has to reckon with N₂. The nitrogen
          molecule appears in DARPA's QB-GSEE target list, in every major VQE paper as a stretch
          goal, and in textbooks as the archetype of a strongly correlated system. It is hard for
          a specific, well-understood reason: the triple bond — one σ and two π bonds — creates a
          six-orbital active space where the Hartree-Fock reference is a poor starting point and
          standard single-reference methods struggle.
        </p>

        <p>
          We added N₂ to the QEncode Suite v4.0 catalog at the start of this year. It took until
          Suite v4.1 to certify it. This post explains what made it hard, what we changed, and
          what the certified result means.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why N₂ is different</h2>

        <p>
          The molecules we certified in v4.0 — H₂, HF, LiH, BeH₂, H₂O, NH₃ — all share a
          property: Hartree-Fock molecular orbitals cleanly partition the active space. You freeze
          the core, pick the frontier orbitals, and the VQE circuit has a sensible starting point.
          N₂ breaks this pattern.
        </p>

        <p>
          The [6e, 6o] active space for N₂ covers the full triple-bond manifold: σ, σ*, πₓ, πₓ*,
          πᵧ, πᵧ*. In the cc-pVDZ basis, Hartree-Fock does not cleanly separate these six orbitals
          from the rest of the virtual space. The π and σ* orbitals mix with higher virtuals, and
          the resulting active space is poorly conditioned for VQE. The circuit starts far from the
          CASCI minimum and COBYLA, a gradient-free optimizer, cannot navigate there reliably from
          that starting point.
        </p>

        <p>
          This is not a deficiency of the benchmark — it is the point. N₂ exposes the difference
          between a well-set-up VQE calculation and one that is just running the default pipeline.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The fix: CASSCF orbital optimization</h2>

        <p>
          The solution is to pre-optimize the molecular orbitals before building the qubit
          Hamiltonian. CASSCF — Complete Active Space Self-Consistent Field — runs an iterative
          procedure that rotates the orbital basis to minimize the energy of the active space
          directly. For N₂, this means the six orbitals passed into the VQE circuit are already
          the best possible representation of the triple-bond manifold rather than the generic
          Hartree-Fock canonical orbitals.
        </p>

        <p>
          In practice the CASSCF and CASCI energies for N₂ are identical to twelve decimal places
          (-109.0899581524 Ha) — confirming that the orbital basis is fully converged before a
          single VQE evaluation runs. The qubit Hamiltonian is then built from these optimized
          orbitals, giving UCCSD a sensible starting point.
        </p>

        <p>
          We added CASSCF support to the generator in Suite v4.1 as a first-class flag:
        </p>

        <pre className="bg-muted rounded-md p-4 text-sm font-mono overflow-x-auto">
{`python scripts/generate_entry_v4.py \\
  --molecule N2 --mapping jordan_wigner \\
  --ansatz-type uccsd --orbital-opt casscf \\
  --multistart 1 --max-iter 10000`}
        </pre>

        <h2 className="text-xl font-semibold mt-8 mb-3">12 qubits, Z2 tapering, 404 parameters</h2>

        <p>
          N₂ in the JW encoding with a [6e, 6o] active space requires 12 qubits — one per
          spin-orbital. Before running VQE we apply Z2 symmetry tapering, which identifies four
          conserved symmetry sectors and eliminates them, reducing the circuit to 8 qubits. The
          tapered Hamiltonian has 378 Pauli terms. Exact diagonalization confirms the ground state
          energy at -109.0899581524 Ha, matching CASCI to 1.1 × 10⁻¹³ Ha — the taper is exact.
        </p>

        <p>
          On the ansatz side, UCCSD for a [6e, 6o] system generates all symmetry-allowed single
          and double excitation operators. After tapering, this produces 404 variational parameters.
          For comparison, H₂ UCCSD has 4 parameters and LiH has around 20. The jump to 404 changes
          the optimization problem fundamentally.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why HEA failed — and what it tells us</h2>

        <p>
          Before committing to UCCSD, we ran the hardware-efficient ansatz with 4 layers (40
          parameters) and 30 random restarts at 500 iterations each. Every single restart hit the
          iteration limit without converging. The best result after 15,000 function evaluations
          was a gap of 0.12 Ha — twelve times the certification threshold.
        </p>

        <p>
          This is a meaningful data point, not a failure to discard. HEA is a generic circuit with
          no chemistry built in. For small, weakly correlated molecules it is competitive with
          UCCSD. For N₂, the rugged energy landscape with 40 free parameters and no physical
          structure means COBYLA gets trapped. The benchmark is doing its job: distinguishing
          ansatz families under real conditions.
        </p>

        <p>
          The HEA result is recorded in the Research tab of the leaderboard as a validated (not
          certified) entry — honest, reproducible, and informative.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The certified result</h2>

        <p>
          With CASSCF orbitals, UCCSD, and 10,000 COBYLA iterations starting from the HF reference
          (all-zero parameters, corresponding to the Hartree-Fock state), the optimizer reached a
          VQE energy of -109.0879426090 Ha against a CASCI reference of -109.0899581524 Ha.
        </p>

        <div className="bg-muted/40 border rounded-lg p-5 my-6 font-mono text-sm space-y-1">
          <div className="flex justify-between"><span className="text-muted-foreground">CASCI (target)</span><span>-109.0899581524 Ha</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">VQE best energy</span><span>-109.0879426090 Ha</span></div>
          <div className="flex justify-between border-t pt-2 mt-2"><span className="text-muted-foreground">Gap |VQE − CASCI|</span><span className="text-green-600 dark:text-green-400 font-semibold">2.015 × 10⁻³ Ha</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Certification threshold</span><span>10 × 10⁻³ Ha</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Chemical accuracy</span><span>1.6 × 10⁻³ Ha</span></div>
        </div>

        <p>
          The gap of 2.015 mHa is certified — well under the 10 mHa threshold. It is also close
          to chemical accuracy (1.6 mHa), though not quite there. For a [6e, 6o] strongly
          correlated system on 8 qubits with a gradient-free optimizer, this is a solid result.
          The entry carries the <em>beats_classical</em> flag: the VQE correlation energy exceeds
          the CCSD(T) correlation energy, meaning the quantum ansatz captures more electron
          correlation than the gold-standard classical approximation on this active space.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What CASSCF changes — and when it matters</h2>

        <p>
          CASSCF orbital optimization is now a first-class option in the QEncode generator but is
          not the default. For most molecules in the suite — H₂, HF, BeH₂, H₂O, NH₃ — HF orbitals
          work well and CASSCF adds computation time without improving the result. N₂ is different
          because the triple bond creates near-degeneracy in the orbital energies that HF cannot
          resolve.
        </p>

        <p>
          The practical rule: if a molecule has multiple bonds of the same type (triple bonds,
          conjugated π systems, transition metal d-orbitals), CASSCF orbital optimization is
          recommended. For single-bond dominated systems, HF is sufficient. This is noted in the
          molecule catalog and surfaced as the CASSCF badge on the leaderboard for entries that
          used it.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Relevance to DARPA QB-GSEE</h2>

        <p>
          DARPA's Quantum Benchmarking program (QB-GSEE) targets ground-state energy estimation
          for molecules where classical methods are insufficient. N₂ appears explicitly in their
          target list as a near-term benchmark candidate. Our certified result at cc-pVDZ with a
          [6e, 6o] active space is directly comparable to the QB-GSEE target specification.
        </p>

        <p>
          The QEncode certification framework — provenance hash, CASCI reference, trust level,
          signed entry — provides exactly the kind of verifiable, reproducible evidence that
          program-level benchmarking requires.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What comes next: benzene</h2>

        <p>
          The natural next step is benzene — the first aromatic molecule in the suite. Benzene
          has a [6e, 6o] π active space with the same qubit count as N₂ but more complex
          correlation structure from the conjugated ring. It also has direct relevance to
          pharmaceutical chemistry, where aromatic rings appear in nearly every drug molecule.
        </p>

        <p>
          We expect CASSCF orbital optimization to be equally critical for benzene, and we will
          need the GPU backend (lightning.gpu) for practical runtime at this scale. The Suite v4.2
          milestone is a certified benzene entry on the public leaderboard.
        </p>

        <p>
          The N₂ result and the new generator capabilities — CASSCF, GPU backend, checkpoint
          restart, early-stop certification — are available now in the open-source repository.
          All entries are reproducible with a single command using the pinned
          requirements-v4.txt environment.
        </p>

        <div className="mt-10 border-t pt-8 flex flex-col sm:flex-row gap-3">
          <Link
            href="/leaderboard"
            className="inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            View N₂ on the leaderboard →
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
