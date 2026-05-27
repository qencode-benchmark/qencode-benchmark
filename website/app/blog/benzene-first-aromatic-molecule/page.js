import Link from "next/link";

export const metadata = {
  title: "Benzene on the Leaderboard: QEncode's First Aromatic Molecule",
  description:
    "Benzene is the gateway to pharmaceutical chemistry. We added it to the QEncode Suite v4.2 — 12 qubits, CASSCF orbital optimization, 914 Pauli terms, and the first aromatic molecule on the public leaderboard.",
  alternates: { canonical: "/blog/benzene-first-aromatic-molecule" },
  openGraph: {
    title: "Benzene on the Leaderboard: QEncode's First Aromatic Molecule",
    description:
      "How QEncode added benzene to its benchmark suite — 12 qubits, 63 HEA parameters, CASSCF orbital optimization, and what an aromatic π system means for VQE.",
    url: "https://www.qencode-benchmark.org/blog/benzene-first-aromatic-molecule",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "Benzene on the Leaderboard: QEncode's First Aromatic Molecule",
  description:
    "Benzene is the gateway to pharmaceutical chemistry. We added it to QEncode Suite v4.2 — 12 qubits, CASSCF orbital optimization, 914 Pauli terms, and the first aromatic molecule on the public leaderboard.",
  datePublished: "2026-05-27",
  dateModified: "2026-05-27",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/benzene-first-aromatic-molecule",
  keywords: [
    "benzene VQE", "aromatic molecule", "quantum benchmark", "CASSCF", "HEA", "12 qubit",
    "pharmaceutical quantum chemistry", "QEncode v4.2",
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
          <time dateTime="2026-05-27">May 27, 2026</time>
          <span>·</span>
          <span>6 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          Benzene on the Leaderboard: QEncode's First Aromatic Molecule
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Nearly every drug molecule contains an aromatic ring. Benzene is the simplest of them —
          six carbons, six hydrogens, six π electrons in a conjugated ring that Hartree-Fock cannot
          correctly describe. We added it to Suite v4.2. Here is what the run required and what
          the result tells us.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <p>
          When we certified N₂ in Suite v4.1, the challenge was the triple bond — a strongly
          correlated system where Hartree-Fock orbitals fail and CASSCF is required. Benzene
          presents the same fundamental challenge through a different structure: six π electrons
          delocalized across a symmetric ring. The orbitals are not localized, the correlation
          is spread across the entire molecule, and standard single-reference methods struggle
          with the same classes of excitations.
        </p>

        <p>
          The practical motivation is pharmaceutical. The aromatic ring is present in roughly
          70% of approved drug molecules — aspirin, caffeine, ibuprofen, most antibiotics.
          Any quantum chemistry method that cannot handle aromatic systems cannot contribute
          to drug discovery. Benzene is the entry point to that class of chemistry.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The active space: 6 π electrons in 6 π orbitals</h2>

        <p>
          In benzene's [6e, 6o] active space, we include the six π-type molecular orbitals —
          three bonding (π₁, π₂, π₃) and three antibonding (π₄*, π₅*, π₆*) — along with the
          six electrons that occupy them at equilibrium. This is the Hückel picture of benzene's
          aromatic system: the electrons that make the ring stable, reactive, and chemically
          interesting.
        </p>

        <p>
          The active space has the same dimensions as N₂ — both are [6e, 6o] — which means
          the same qubit count (12 in Jordan-Wigner encoding) and comparable circuit complexity.
          The structural difference is symmetry: N₂ has linear D∞h symmetry and a concentrated
          triple bond; benzene has hexagonal D6h symmetry and a delocalized ring. Both require
          CASSCF orbital optimization.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why CASSCF is required</h2>

        <p>
          In Hartree-Fock, the six π orbitals of benzene mix with σ* antibonding orbitals from
          the C-H framework. The result is a set of canonical molecular orbitals that don't
          cleanly represent the π system. If you build the VQE Hamiltonian from these mixed
          orbitals, the circuit has no good starting point — the CASCI minimum is hidden behind
          a large orbital-basis error.
        </p>

        <p>
          CASSCF pre-optimizes the orbital basis to minimize the energy of the active space
          before any VQE evaluation runs. For benzene, this means the six π orbitals passed
          to the circuit genuinely represent the aromatic system — they are the orbitals where
          the interesting chemistry lives.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The run: 12 → 9 qubits, 914 Pauli terms</h2>

        <p>
          After CASSCF orbital optimization, we build the qubit Hamiltonian in the Jordan-Wigner
          encoding. Benzene's [6e, 6o] active space maps to 12 qubits — one per spin-orbital.
          Z2 symmetry tapering identifies three conserved symmetry sectors in the D6h Hamiltonian
          and removes them, reducing the circuit to 9 qubits. The tapered Hamiltonian has 914
          Pauli terms — larger than N₂ (378 terms) due to benzene's greater structural complexity.
        </p>

        <p>
          We ran the Hardware-Efficient Ansatz (HEA) with 6 repetition layers and 63 parameters,
          using 30 random restarts at 500 COBYLA iterations each. The circuit uses alternating
          layers of single-qubit rotations and entangling CNOT gates — no chemistry built in,
          but a flexible enough structure to explore the energy landscape broadly.
        </p>

        <div className="bg-muted/40 border rounded-lg p-5 my-6 font-mono text-sm space-y-1">
          <div className="flex justify-between"><span className="text-muted-foreground">Active space</span><span>[6e, 6o]</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Qubits (JW → tapered)</span><span>12 → 9</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Z2 symmetries removed</span><span>3</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Pauli terms</span><span>914</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Ansatz parameters (HEA reps=6)</span><span>63</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Restarts</span><span>30</span></div>
          <div className="flex justify-between border-t pt-2 mt-2"><span className="text-muted-foreground">Gap |VQE − CASCI|</span><span className="font-semibold">91.1 mHa</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">Tier</span><span>Research (gap &gt; 10 mHa)</span></div>
          <div className="flex justify-between"><span className="text-muted-foreground">beats_classical</span><span className="text-green-600 dark:text-green-400">True</span></div>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">What 91.1 mHa means</h2>

        <p>
          The HEA result does not certify — the 91.1 mHa gap is well above our 10 mHa
          certification threshold. This is expected. HEA with 63 parameters and a gradient-free
          optimizer is not designed for a 914-term Hamiltonian with strong π correlation. The
          energy landscape is rugged, the restarts explore it broadly, and the result is the
          best the general-purpose circuit can find.
        </p>

        <p>
          The <em>beats_classical</em> flag — which records whether the VQE correlation energy
          exceeds the CCSD(T) correlation energy — is True for this entry. This is a separate
          measure from the gap: even at 91 mHa from the active-space exact answer, the VQE
          circuit captures more electron correlation than the classical gold-standard method on
          this active space. That reflects how difficult benzene's π correlation is for
          perturbative methods.
        </p>

        <p>
          The result is recorded in the Research tab of the leaderboard — honest, reproducible,
          and informative. Research-tier entries are not failures; they are data points that
          document the current frontier of what standard ansatz families achieve.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The reproduce command</h2>

        <pre className="bg-muted rounded-md p-4 text-sm font-mono overflow-x-auto">
{`python scripts/generate_entry_v4.py \\
  --molecule benzene --mapping jordan_wigner \\
  --ansatz-type hea --ansatz-reps 6 \\
  --orbital-opt casscf --multistart 30 \\
  --max-iter 500 --out-dir releases/v4/db`}
        </pre>

        <h2 className="text-xl font-semibold mt-8 mb-3">What comes next: UCCSD and hydrogen chains</h2>

        <p>
          Benzene UCCSD — with approximately 400 parameters, the same scale as N₂ — is the
          next target. A UCCSD certification of benzene would be the first aromatic molecule
          at chemical-accuracy-class precision in the suite, and a meaningful milestone for
          pharmaceutical quantum chemistry relevance.
        </p>

        <p>
          In parallel, Suite v4.3 will add hydrogen chains — H₄, H₆, H₈ — which appear
          explicitly in the DARPA QB-GSEE target list. Hydrogen chains are cheap to run,
          systematically scalable, and ideal for testing how benchmark performance degrades
          as the active space grows.
        </p>

        <p>
          All entries — including the benzene HEA Research result — are open source,
          reproducible with a single command, and signed with an Ed25519 provenance hash.
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
