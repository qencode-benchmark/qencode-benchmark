import Link from "next/link";

export const metadata = {
  title: "Why VQE Benchmarks Are So Hard to Reproduce — and How QEncode Fixes It",
  description:
    "Most published VQE results cannot be reproduced. The reasons are technical but fixable: underdocumented ansatz construction, hardware-specific transpilation, and no standard error metric. QEncode addresses all three.",
  alternates: { canonical: "/blog/vqe-benchmarking-reproducibility" },
  openGraph: {
    title: "Why VQE Benchmarks Are So Hard to Reproduce — and How QEncode Fixes It",
    description:
      "Most published VQE results cannot be reproduced. QEncode defines a standard that makes quantum algorithm benchmarks verifiable and comparable.",
    url: "https://www.qencode-benchmark.org/blog/vqe-benchmarking-reproducibility",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "Why VQE Benchmarks Are So Hard to Reproduce — and How QEncode Fixes It",
  description:
    "Most published VQE results cannot be reproduced. The reasons are technical but fixable: underdocumented ansatz construction, hardware-specific transpilation, and no standard error metric. QEncode addresses all three.",
  datePublished: "2026-04-18",
  dateModified: "2026-04-18",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/vqe-benchmarking-reproducibility",
  keywords: ["VQE reproducibility", "quantum benchmark", "ansatz", "QEncode"],
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
          <time dateTime="2026-04-18">April 18, 2026</time>
          <span>·</span>
          <span>6 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          Why VQE Benchmarks Are So Hard to Reproduce — and How QEncode Fixes It
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Most published VQE results can't be reproduced. The reasons are technical but fixable:
          underdocumented ansatz construction, hardware-specific transpilation, and no standard
          error metric. Here&apos;s how QEncode addresses all three.
        </p>
      </div>

      {/* Body */}
      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <p>
          Quantum chemistry is one of the most promising near-term applications of quantum
          computing. The Variational Quantum Eigensolver (VQE) algorithm, introduced in 2014,
          has been the subject of hundreds of papers, dozens of hardware demonstrations, and
          significant investment from both academia and industry. Yet if you try to take a
          published VQE result and reproduce it — even with the same code and the same molecule
          — you will frequently fail.
        </p>

        <p>
          This is not a fringe problem. A 2023 survey of quantum chemistry benchmark papers
          found that fewer than 30% provided enough information to independently reproduce the
          reported energy estimates. The reproducibility crisis that has affected classical
          computational science for decades is arriving in quantum computing — and arriving early,
          before the field has established the norms to handle it.
        </p>

        <p>
          Understanding why this happens — and what a rigorous standard looks like — matters for
          anyone evaluating quantum algorithms or comparing competing approaches.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">Why VQE results don't reproduce</h2>

        <p>
          The failure modes are consistent and predictable. They cluster around three root causes.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">1. Underspecified ansatz construction</h3>

        <p>
          The ansatz — the parameterized circuit that VQE optimizes — is the most consequential
          design choice in the algorithm. A paper might report using "UCCSD" without specifying
          which Hartree-Fock reference state was used, how the excitation operators were ordered,
          whether spin symmetry was enforced, or how the Jordan-Wigner mapping was applied.
          These details change the circuit, which changes the result.
        </p>

        <p>
          Similarly, hardware-efficient ansatz descriptions often omit the specific gate set,
          entanglement topology, and number of layers — all of which directly determine the
          circuit's expressibility and therefore the achievable energy.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">2. Hardware-specific transpilation</h3>

        <p>
          When circuits run on real quantum hardware, they must be transpiled — compiled down to
          the native gate set and connectivity of the specific device. Different devices produce
          different transpiled circuits from the same logical circuit. A result obtained on an
          IBM Falcon processor cannot be directly compared to one from a Quantinuum H-series
          device, even for the same molecule and ansatz, because the compiled circuits are
          different.
        </p>

        <p>
          Papers often report results from a specific hardware run without clearly separating
          the algorithmic performance from device-specific effects. This makes it impossible to
          know whether a reported improvement comes from the algorithm or from favorable
          hardware characteristics.
        </p>

        <h3 className="text-lg font-semibold text-foreground mt-8 mb-2">3. No standard error metric</h3>

        <p>
          Different papers use different metrics to evaluate VQE accuracy. Some report absolute
          energy error in Hartree. Others report correlation energy recovery percentage. Some use
          the ground state fidelity. Some don't report an error metric at all, only that the
          result is "close to FCI."
        </p>

        <p>
          Without a standard metric, comparison across papers is meaningless. A result that
          looks better by one metric may be worse by another, and "chemical accuracy" (typically
          defined as 1.6 × 10⁻³ Hartree, or 1 kcal/mol) is often cited without being rigorously
          demonstrated.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">What a rigorous benchmark standard requires</h2>

        <p>
          These are not unsolvable problems. Classical computational chemistry solved equivalent
          issues decades ago through standardized benchmarks — G2, G3, W4, GMTKN55 — that
          specify exact molecular geometries, basis sets, methods, and reference energies. Every
          new method is evaluated against the same standard problems with the same metrics.
        </p>

        <p>
          Quantum algorithm benchmarking needs the same thing. A rigorous standard requires:
        </p>

        <ul className="list-disc pl-6 space-y-2">
          <li>
            <strong>Fixed molecular geometries and Hamiltonians.</strong> The electronic
            Hamiltonian for each benchmark molecule must be generated from a specified geometry
            and basis set using a reproducible procedure.
          </li>
          <li>
            <strong>Specified qubit mappings.</strong> The fermionic-to-qubit mapping must be
            declared (Jordan-Wigner, parity, Bravyi-Kitaev) with all reduction steps documented.
          </li>
          <li>
            <strong>Exact reference energies.</strong> FCI energies computed with the same
            Hamiltonian serve as the ground truth against which VQE accuracy is measured.
          </li>
          <li>
            <strong>A standard error metric.</strong> The energy gap — absolute difference
            between VQE estimate and FCI energy — gives a hardware-agnostic, universally
            interpretable accuracy measure.
          </li>
          <li>
            <strong>Hardware-agnostic circuit metrics.</strong> Circuit depth and two-qubit gate
            count, measured before hardware transpilation, give a device-independent cost metric
            that enables fair comparison across platforms.
          </li>
          <li>
            <strong>Managed, reproducible execution.</strong> All benchmark circuits should run
            on the same simulation infrastructure under identical conditions, with results
            independently verified.
          </li>
        </ul>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">How QEncode Suite v2 implements this</h2>

        <p>
          QEncode Suite v2 is a benchmark specification and managed execution service built
          around exactly these requirements. The suite defines five benchmark molecules — H₂,
          LiH, HF, N₂, and BeH₂ — with fixed geometries, basis sets (STO-3G for smaller
          molecules, cc-pVDZ for larger), and exact FCI reference energies computed with PySCF.
        </p>

        <p>
          Every submitted algorithm is evaluated at all three standard qubit encodings
          (Jordan-Wigner, parity, Bravyi-Kitaev) with Qiskit-generated Hamiltonians, producing
          comparable results across the encoding spectrum. Circuit metrics are recorded
          post-transpilation at a fixed optimization level, giving a fair hardware-agnostic cost
          estimate.
        </p>

        <p>
          The energy gap against FCI is the primary accuracy metric across all leaderboard
          categories. Results are signed with an Ed25519 key, producing a verifiable
          certification receipt that can be independently checked.
        </p>

        <h2 className="text-xl font-semibold text-foreground mt-10 mb-3">Why this matters for algorithm developers</h2>

        <p>
          If you're developing a new ansatz, optimizer, or error mitigation technique, the
          inability to make reproducible benchmark claims is a real problem. Reviewers and
          customers can't evaluate your results against the state of the art if everyone's using
          different benchmarks. Worse, it's easy to overfit to a specific benchmark setup and
          report numbers that don't generalize.
        </p>

        <p>
          A certified QEncode result gives you a reproducible, independently verified benchmark
          claim that you can publish, share, and defend — because it was produced by the same
          standard infrastructure as every other entry on the leaderboard. When your result
          appears on the leaderboard, the comparison is meaningful because the benchmark
          conditions are identical.
        </p>

        <p>
          Reproducibility isn't just a scientific virtue. For quantum computing to make its case
          to industry, results need to be verifiable. QEncode Suite v2 is designed to make that
          possible.
        </p>

        <div className="mt-10 p-5 rounded-lg border bg-muted/40">
          <p className="text-sm font-medium text-foreground mb-2">Read the full benchmark specification</p>
          <p className="text-sm text-muted-foreground mb-4">
            The QEncode Suite v2 specification documents all molecule geometries, Hamiltonian
            generation procedures, encoding definitions, metric formulas, and certification
            requirements.
          </p>
          <div className="flex gap-3">
            <Link
              href="/benchmark"
              className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            >
              Benchmark spec
            </Link>
            <Link
              href="/leaderboard"
              className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium text-foreground hover:bg-accent transition-colors"
            >
              View leaderboard
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
