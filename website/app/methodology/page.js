import Link from "next/link";
import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "Benchmark Methodology — Suite v4",
  description:
    "QEncode Suite v4 benchmark methodology: PySCF CASCI reference, optional CASSCF orbital optimization, PennyLane VQE, Z2 tapering, COBYLA / L-BFGS-B / Adam optimizers, cc-pVDZ basis, Ed25519 provenance signing.",
  keywords: [
    "quantum benchmark methodology",
    "VQE methodology",
    "CASSCF orbital optimization",
    "leaderboard scoring rules",
    "quantum ranking criteria",
    "cc-pVDZ VQE"
  ],
  alternates: { canonical: "/methodology" },
  openGraph: {
    title: "QEncode Benchmark Methodology — Suite v4",
    description:
      "Fixed benchmark execution pipeline with CASSCF orbital optimization, CASCI reference energies, and Ed25519-signed provenance for reproducible quantum leaderboard rankings.",
    url: "https://www.qencode-benchmark.org/methodology"
  }
};

export default function MethodologyPage() {
  return (
    <div className="container py-16 max-w-4xl">
      <div className="mb-10">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <h1 className="text-3xl sm:text-4xl font-bold">Benchmark Methodology</h1>
          <Badge variant="secondary" className="text-xs font-mono">Suite v4</Badge>
        </div>
        <p className="text-muted-foreground max-w-2xl">
          QEncode uses a fixed, fully reproducible execution pipeline. Every entry — whether self-run or
          managed — follows the same pipeline, the same reference, and the same scoring rules.
          No manual adjustment of results is ever made.
        </p>
      </div>

      {/* Pipeline */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Execution Pipeline</h2>
        <div className="rounded-lg border bg-muted/30 p-6 space-y-5 text-sm text-muted-foreground leading-relaxed">

          <div>
            <p className="font-medium text-foreground mb-1">1. Classical reference — PySCF</p>
            <p>
              PySCF computes the quantum chemistry reference at the molecule&apos;s geometry and cc-pVDZ basis.
              Outputs: HF, MP2, CCSD, CCSD(T) energies, and — critically — the CASCI active-space FCI energy.
              The CASCI energy is the VQE target. All accuracy gaps are measured as{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">|E_VQE − E_CASCI|</code>, never
              against full-system FCI or a classical approximation.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground mb-1">2. CASSCF orbital optimization (optional, required for some)</p>
            <p>
              For molecules with strong multireference character — currently N₂, H₆, benzene, and H₈ — HF canonical
              orbitals do not cleanly partition the active space. QEncode runs CASSCF to pre-optimise the
              orbital basis before building the qubit Hamiltonian. The flag is{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">--orbital-opt casscf</code>.
              For N₂, CASSCF and CASCI energies converge to twelve decimal places, confirming the orbital
              basis is fully converged before a single VQE evaluation runs. HF orbital optimization is the
              default for all other molecules.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground mb-1">3. Qubit Hamiltonian — PennyLane</p>
            <p>
              PennyLane builds the molecular Hamiltonian from the active-space integrals using the selected
              qubit mapping: Jordan-Wigner (direct, all molecules), Parity (via OpenFermion bridge, all
              molecules), or Bravyi-Kitaev (H₂ and HF only — PL 0.45 imaginary artefacts excluded larger
              molecules). The Hamiltonian is expressed as a sum of weighted Pauli operators.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground mb-1">4. Z2 symmetry tapering</p>
            <p>
              Conserved Z2 symmetry sectors are identified and eliminated, reducing the qubit count.
              H₂ and HF go from 4 → 1 qubit (3 symmetries removed). N₂ goes from 12 → 8 qubits
              (4 symmetries removed). The tapered HF reference state is computed with{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">qchem.taper_hf()</code>.
              For BK tapering (H₂ and HF only), imaginary parts are verified to be below{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">1e-6 × max_abs</code> before the
              strip is applied.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground mb-1">5. VQE — COBYLA / L-BFGS-B / Adam</p>
            <p>
              The variational quantum eigensolver runs with one of three optimizers: COBYLA
              (gradient-free, the suite default), L-BFGS-B (quasi-Newton, driven by analytic
              parameter-shift gradients), or Adam (stochastic gradient descent). Ansatz: UCCSD
              (tapered symmetry-adapted excitation operators), HEA (hardware-efficient alternating
              rotation/entanglement layers, configurable{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">--reps</code>), or ADAPT-VQE
              (operators selected one at a time from the UCCSD pool by parameter-shift gradient
              magnitude, giving a far shorter parameter vector than full UCCSD).
            </p>
            <div className="mt-3 rounded-md bg-muted p-3 text-xs font-mono space-y-1">
              <p className="text-foreground font-semibold text-sm font-sans mb-2">Run config by molecule class</p>
              <p>Small molecules (H₂, HF, LiH, BeH₂, H₂O, NH₃) — HEA: max_iter=500, multistart=10</p>
              <p>Small molecules — UCCSD: max_iter=500, multistart=10</p>
              <p>Hydrogen chains (H₄, H₆) — HEA: max_iter=500, multistart=1–10; UCCSD: max_iter=1,000, multistart=1</p>
              <p>N₂ UCCSD (404 params): max_iter=10,000, multistart=1 (HF zeros initialization)</p>
              <p>ADAPT-VQE (H₂CO, C₄H₆, H₄, H₆, N₂, benzene, H₈) — COBYLA inner loop: max_iter=200–500, multistart=1</p>
              <p>Early-stop: fires when gap &lt; 0.01 Ha, records actual restarts completed</p>
            </div>
            <p className="mt-3">
              Circuit metrics (depth, two-qubit gate count, T-gate estimate) are recorded post-VQE using
              the default PennyLane transpiler. A <em>Beats Classical</em> flag is set when the VQE
              correlation energy exceeds the CCSD(T) correlation energy.
            </p>
          </div>

          <div>
            <p className="font-medium text-foreground mb-1">6. Provenance and signing</p>
            <p>
              Each entry is assigned a compound ID containing molecule, basis, mapping, ansatz, and a
              16-character SHA-256 hash of the full JSON payload. Certified entries are signed with an
              Ed25519 key. The JSON entry includes all PySCF energies, VQE trajectory, circuit metrics,
              FCIDUMP integrals (base64), run config, and the signature. Entries are stored in{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">releases/v4/db/</code> in the
              public GitHub repository.
            </p>
          </div>
        </div>
      </section>

      {/* Leaderboard Rules */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Leaderboard Rules</h2>
        <div className="space-y-3">
          <div className="rounded-lg border p-4">
            <h3 className="font-semibold text-sm mb-1">Eligibility</h3>
            <p className="text-sm text-muted-foreground">
              Suite v4 match + <code className="font-mono text-xs bg-muted px-1 rounded">trust_level = certified</code>{" "}
              (gap &lt; 0.01 Ha). Entries with gap ≥ 0.01 Ha appear in the Research tab only as validated
              results — honest, reproducible, but not certified. No result is ever discarded or adjusted.
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="font-semibold text-sm mb-1">Accuracy ranking</h3>
            <p className="text-sm text-muted-foreground">
              Sort by lowest <code className="font-mono text-xs bg-muted px-1 rounded">|E_VQE − E_CASCI|</code>{" "}
              in Hartrees. Lower is better. Two thresholds are shown:{" "}
              <span className="font-medium text-foreground">chemical accuracy (1.6 mHa)</span> and{" "}
              <span className="font-medium text-foreground">certification threshold (10 mHa)</span>.
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="font-semibold text-sm mb-1">Hardware cost ranking</h3>
            <p className="text-sm text-muted-foreground">
              Sort by fewest two-qubit gates (tie-break: circuit depth). Excludes UCCSD entries on H₂
              and HF where circuit depth is symbolic (PennyLane does not transpile UCCSD to native gates
              for 1-qubit tapered circuits). Requires transpiled circuit metrics to appear on this tab.
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="font-semibold text-sm mb-1">Balanced score</h3>
            <p className="text-sm text-muted-foreground">
              Rank-normalised combined score:{" "}
              <code className="font-mono text-xs bg-muted px-1 rounded">
                0.5 × (gap_rank / (N−1)) + 0.5 × (cost_rank / (N−1))
              </code>{" "}
              ∈ [0, 1]. Lower is better. Requires circuit metrics. N = certified entries with metrics.
            </p>
          </div>
          <div className="rounded-lg border p-4">
            <h3 className="font-semibold text-sm mb-1">Research tab</h3>
            <p className="text-sm text-muted-foreground">
              Validated entries (gap ≥ 0.01 Ha) are shown here. Example: N₂ JW/HEA with reps=4 achieved
              a best gap of 0.121 Ha across 30 restarts — 12× the threshold, showing HEA cannot navigate
              the N₂ energy landscape with 40 parameters. This is a meaningful data point, not a failure
              to discard. The benchmark records what actually happened.
            </p>
          </div>
        </div>
      </section>

      {/* Data provenance */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Data Provenance</h2>
        <div className="rounded-lg border p-6 bg-muted/30 text-sm text-muted-foreground leading-relaxed space-y-2">
          <p>
            All v4 entries are stored as JSON artifacts in{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">releases/v4/db/</code> in the
            public GitHub repository. Leaderboard CSVs are generated by{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">scripts/export_leaderboard_v4.py</code>{" "}
            directly from those entry files — no manual editing, no cherry-picking.
            Deduplication keeps the best gap per (molecule, mapping, ansatz, orbital_opt) combination.
          </p>
          <p>
            The pipeline is version-locked:{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">requirements-v4.txt</code> pins
            PySCF 2.5.0, PennyLane 0.45, openfermion 1.7.1, and NumPy. Any run using this environment
            on the same molecule will reproduce the same reference energies.
          </p>
          <p>
            v3 entries are frozen and remain reproducible with{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">requirements-v3.txt</code> via
            <code className="font-mono text-xs bg-muted px-1 rounded"> scripts/verify_entry.py</code>.
          </p>
        </div>
      </section>

      {/* CTA */}
      <div className="flex flex-wrap gap-3">
        <Link
          href="/benchmark"
          className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          ← Benchmark Spec
        </Link>
        <Link
          href="/leaderboard"
          className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
        >
          View leaderboard
        </Link>
        <a
          href="https://github.com/qencode-benchmark/qencode-benchmark"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
        >
          GitHub → generate_entry_v4.py
        </a>
      </div>
    </div>
  );
}
