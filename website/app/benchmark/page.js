import Link from "next/link";
import { CheckCircle, Clock, AlertCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "Benchmark Specification — Suite v4",
  description:
    "QEncode Suite v4 benchmark specification: 10 molecules, cc-pVDZ basis, chemistry-driven active spaces, Jordan-Wigner / Parity / Bravyi-Kitaev encodings, UCCSD and HEA ansatz, CASSCF orbital optimization.",
  keywords: [
    "quantum benchmark specification",
    "suite v4",
    "VQE molecules",
    "Jordan-Wigner Bravyi-Kitaev Parity",
    "UCCSD HEA",
    "cc-pVDZ",
    "CASSCF VQE"
  ],
  alternates: { canonical: "/benchmark" },
  openGraph: {
    title: "QEncode Benchmark Specification — Suite v4",
    description:
      "Fixed benchmark definitions for 10 molecules at cc-pVDZ basis with chemistry-driven active spaces, three qubit encodings, and two ansatz families.",
    url: "https://www.qencode-benchmark.org/benchmark"
  }
};

const molecules = [
  {
    name: "H₂",
    formula: "Hydrogen",
    activeSpace: "[2e, 2o]",
    qubitsJW: 4,
    qubitsTagered: 1,
    symRemoved: 3,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR", "BK"],
    casscf: false,
    tier: "certified",
    certifiedEntries: 6,
    notes: "Full valence σ/σ* space. BK tapering fully supported.",
  },
  {
    name: "HF",
    formula: "Hydrogen Fluoride",
    activeSpace: "[2e, 2o]",
    qubitsJW: 4,
    qubitsTagered: 1,
    symRemoved: 3,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR", "BK"],
    casscf: false,
    tier: "certified",
    certifiedEntries: 6,
    notes: "F 2p HOMO + LUMO. BK tapering fully supported.",
  },
  {
    name: "LiH",
    formula: "Lithium Hydride",
    activeSpace: "[4e, 4o]",
    qubitsJW: 8,
    qubitsTagered: 5,
    symRemoved: 3,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: false,
    tier: "certified",
    certifiedEntries: 3,
    notes: "BK excluded — PL 0.45 imaginary artefact. PAR/UCCSD excluded.",
  },
  {
    name: "BeH₂",
    formula: "Beryllium Hydride",
    activeSpace: "[4e, 4o]",
    qubitsJW: 8,
    qubitsTagered: null,
    symRemoved: null,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: false,
    tier: "certified",
    certifiedEntries: 4,
    notes: "Linear D∞h symmetry. PAR/UCCSD works here (exception). BK excluded.",
  },
  {
    name: "H₂O",
    formula: "Water",
    activeSpace: "[4e, 4o]",
    qubitsJW: 8,
    qubitsTagered: null,
    symRemoved: null,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: false,
    tier: "certified",
    certifiedEntries: 3,
    notes: "C2v symmetry. BK excluded. PAR/UCCSD excluded.",
  },
  {
    name: "NH₃",
    formula: "Ammonia",
    activeSpace: "[4e, 4o]",
    qubitsJW: 8,
    qubitsTagered: null,
    symRemoved: null,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: false,
    tier: "certified",
    certifiedEntries: 3,
    notes: "C3v symmetry. BK excluded. PAR/UCCSD excluded.",
  },
  {
    name: "N₂",
    formula: "Nitrogen",
    activeSpace: "[6e, 6o]",
    qubitsJW: 12,
    qubitsTagered: 8,
    symRemoved: 4,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: true,
    tier: "certified",
    certifiedEntries: 1,
    notes: "Full triple-bond σ/σ*/π manifold. Strong multireference. CASSCF required. DARPA QB-GSEE candidate.",
  },
  {
    name: "H₂CO",
    formula: "Formaldehyde",
    activeSpace: "[4e, 4o]",
    qubitsJW: 8,
    qubitsTagered: null,
    symRemoved: null,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: false,
    tier: "target",
    certifiedEntries: 0,
    notes: "C=O π/π* carbonyl correlation. C2v symmetry. New in v4.1.",
  },
  {
    name: "C₄H₆",
    formula: "1,3-Butadiene",
    activeSpace: "[4e, 4o]",
    qubitsJW: 8,
    qubitsTagered: null,
    symRemoved: null,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: false,
    tier: "target",
    certifiedEntries: 0,
    notes: "Conjugated diene π system. C2h symmetry. First conjugated molecule. New in v4.1.",
  },
  {
    name: "Benzene",
    formula: "Benzene (C₆H₆)",
    activeSpace: "[6e, 6o]",
    qubitsJW: 12,
    qubitsTagered: null,
    symRemoved: null,
    basis: "cc-pVDZ",
    mappings: ["JW", "PAR"],
    casscf: true,
    tier: "target",
    certifiedEntries: 0,
    notes: "Aromatic π system. D6h symmetry. CASSCF required. First aromatic molecule. New in v4.2.",
  },
];

const encodings = [
  {
    id: "JW",
    name: "Jordan-Wigner (JW)",
    desc: "Maps each spin-orbital to one qubit. Locality is preserved along the qubit chain. Supported for all Suite v4 molecules.",
    supported: "All molecules",
  },
  {
    id: "PAR",
    name: "Parity (PAR)",
    desc: "Encodes parity information, enabling 2-qubit reduction. Implemented via OpenFermion bridge. UCCSD operators require care — excluded for LiH, H₂O, NH₃, N₂, benzene.",
    supported: "All molecules (HEA); select molecules (UCCSD)",
  },
  {
    id: "BK",
    name: "Bravyi-Kitaev (BK)",
    desc: "Balances locality and non-locality. Tapering verified clean only for H₂ and HF in PennyLane 0.45. Excluded for all larger molecules due to imaginary artefacts.",
    supported: "H₂ and HF only",
  },
];

const ansatzTypes = [
  {
    name: "UCCSD",
    full: "Unitary Coupled Cluster Singles and Doubles",
    desc: "Chemically-motivated ansatz. Excitation operators are generated from the active space. High accuracy but deep circuits — parameter count scales with active space size. N₂ UCCSD has 404 parameters.",
    note: "Chemically preferred. Required for certified leaderboard entries on strongly correlated molecules.",
  },
  {
    name: "HEA",
    full: "Hardware-Efficient Ansatz",
    desc: "Generic parameterised circuit with alternating rotation and entanglement layers. Shallow, hardware-friendly, fast to run. Layer count (reps) is configurable. Sufficient for simple molecules, insufficient for strong multireference systems like N₂.",
    note: "Preferred for near-term hardware experiments. Not always sufficient for certification.",
  },
];

export default function BenchmarkPage() {
  return (
    <div className="container py-16 max-w-5xl">
      <div className="mb-10">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <h1 className="text-3xl sm:text-4xl font-bold">Benchmark Specification</h1>
          <Badge variant="secondary" className="text-xs font-mono">Suite v4</Badge>
        </div>
        <p className="text-muted-foreground max-w-2xl mb-1">
          QEncode uses fixed suite definitions so every run is reproducible and directly comparable across teams.
          All v4 molecules use the cc-pVDZ basis with chemistry-driven active spaces.
        </p>
        <p className="text-xs text-muted-foreground font-mono mt-2">
          Pipeline: PySCF HF → [CASSCF] → CASCI reference · PennyLane Hamiltonian · Z2 tapering · COBYLA VQE
        </p>
      </div>

      {/* Molecule table */}
      <section className="mb-14">
        <h2 className="text-xl font-semibold mb-1">Suite v4 — Molecule Catalog</h2>
        <p className="text-sm text-muted-foreground mb-4">
          7 certified molecules + 3 upcoming targets (H₂CO, C₄H₆, benzene). All use cc-pVDZ basis.
        </p>
        <div className="rounded-lg border overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50 text-left border-b">
                  <th className="px-4 py-3 font-medium text-muted-foreground">Molecule</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Active space</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground text-right">JW qubits</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground text-right">Tapered</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Encodings</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Flags</th>
                  <th className="px-4 py-3 font-medium text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody>
                {molecules.map((m) => (
                  <tr key={m.name} className={`border-t hover:bg-muted/20 transition-colors ${m.tier === "target" ? "opacity-60" : ""}`}>
                    <td className="px-4 py-3">
                      <span className="font-medium">{m.name}</span>
                      <p className="text-xs text-muted-foreground">{m.formula}</p>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{m.activeSpace}</td>
                    <td className="px-4 py-3 text-right font-mono">{m.qubitsJW}</td>
                    <td className="px-4 py-3 text-right font-mono text-muted-foreground">
                      {m.qubitsTagered ?? "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {m.mappings.map((mp) => (
                          <Badge key={mp} variant="outline" className="text-xs font-mono py-0">{mp}</Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {m.casscf && (
                        <Badge className="text-xs bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-0 font-normal">
                          CASSCF
                        </Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {m.tier === "certified" ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400">
                          <CheckCircle className="h-3.5 w-3.5" />
                          {m.certifiedEntries} entries
                        </span>
                      ) : m.name === "Benzene" ? (
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400">
                          <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse inline-block" />
                          v4.2 target
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3.5 w-3.5" /> Upcoming
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Notes callout */}
        <div className="mt-4 rounded-lg border bg-muted/30 p-4 text-xs text-muted-foreground space-y-1.5">
          <p className="font-medium text-foreground text-sm">Encoding exclusion notes</p>
          <p><span className="font-medium text-foreground">BK excluded (LiH, BeH₂, H₂O, NH₃, N₂, H₂CO, C₄H₆, benzene)</span> — PennyLane 0.45 introduces imaginary artefacts (&gt;7 mHa) in BK tapering for active spaces larger than [2,2]. Only H₂ and HF pass the imaginary-strip check.</p>
          <p><span className="font-medium text-foreground">PAR/UCCSD excluded (LiH, H₂O, NH₃, N₂, benzene)</span> — UCCSD excitation operators generated in the JW basis are not correctly adapted for Parity tapering in these active spaces. BeH₂ is the exception: D∞h linear symmetry keeps the operator space well-conditioned.</p>
          <p><span className="font-medium text-foreground">CASSCF required (N₂, benzene)</span> — HF orbitals do not cleanly partition the active space for strongly correlated systems. CASSCF pre-optimises orbitals before the VQE circuit is built.</p>
        </div>
      </section>

      {/* Encodings */}
      <section className="mb-14">
        <h2 className="text-xl font-semibold mb-4">Qubit Encodings</h2>
        <div className="space-y-3">
          {encodings.map((e) => (
            <div key={e.id} className="rounded-lg border p-5">
              <div className="flex items-start justify-between gap-3 mb-2">
                <h3 className="font-semibold">{e.name}</h3>
                <Badge variant="secondary" className="text-xs shrink-0">{e.id}</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-1">{e.desc}</p>
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Supported: </span>{e.supported}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Ansatz */}
      <section className="mb-14">
        <h2 className="text-xl font-semibold mb-4">Ansatz Types</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {ansatzTypes.map((a) => (
            <div key={a.name} className="rounded-lg border bg-card p-5">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-mono text-lg font-semibold">{a.name}</h3>
              </div>
              <p className="text-xs text-muted-foreground mb-2">{a.full}</p>
              <p className="text-sm text-muted-foreground mb-3">{a.desc}</p>
              <p className="text-xs border-t pt-2 text-muted-foreground">
                <span className="font-medium text-foreground">When to use: </span>{a.note}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Reproducibility */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold mb-4">Reproducibility Guarantees</h2>
        <div className="rounded-lg border p-6 bg-muted/30 space-y-3 text-sm text-muted-foreground leading-relaxed">
          <p>
            Every Suite v4 entry is generated by a single script —{" "}
            <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">scripts/generate_entry_v4.py</code>{" "}
            — with a fully pinned environment (<code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">requirements-v4.txt</code>).
            The molecule geometry, basis set, active space, encoding, and ansatz are all predetermined by suite rules.
          </p>
          <p>
            Each entry is identified by a compound ID such as{" "}
            <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">N2_ccpvdz_JW_UCCSD_v4_casscf_tapered__sha256_82e00cea5a20cd83</code>{" "}
            and includes a SHA-256 provenance hash and Ed25519 signature for tamper detection.
            All entries are stored in the public GitHub repository under{" "}
            <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">releases/v4/db/</code>.
          </p>
          <p>
            Reference energies (HF, MP2, CCSD, CCSD(T), CASCI) are computed by PySCF at the same geometry
            and basis. VQE gaps are always measured against E_CASCI — never against full-system FCI or
            a classical approximation.
          </p>
        </div>
      </section>

      {/* CTA */}
      <div className="flex flex-wrap gap-3">
        <Link
          href="/methodology"
          className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Read full methodology →
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
          GitHub → requirements-v4.txt
        </a>
      </div>
    </div>
  );
}
