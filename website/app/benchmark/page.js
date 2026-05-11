export const metadata = {
  title: "Benchmark Specification",
  description:
    "Review QEncode Standard Suite v3 benchmark specifications: 7 molecules, 3 qubit encodings, 2 ansatz types, and reproducibility constraints for fair quantum algorithm comparison.",
  keywords: [
    "quantum benchmark specification",
    "suite v3",
    "VQE molecules",
    "Jordan-Wigner Bravyi-Kitaev Parity",
    "UCCSD HEA"
  ],
  alternates: {
    canonical: "/benchmark"
  },
  openGraph: {
    title: "QEncode Benchmark Specification - Suite v3",
    description:
      "Fixed benchmark definitions for molecules, encodings, ansatz settings, and reproducibility in quantum algorithm testing.",
    url: "/benchmark"
  }
};

export default function BenchmarkPage() {
  const molecules = [
    { name: "H₂",   status: "active",   formula: "Hydrogen",           qubits: "4 (tapered: 1)",  note: "[2,2] active space" },
    { name: "HF",   status: "active",   formula: "Hydrogen Fluoride",   qubits: "4 (tapered: 2)",  note: "[2,2] active space" },
    { name: "LiH",  status: "active",   formula: "Lithium Hydride",     qubits: "12 (tapered: 8)", note: "[4,4] active space" },
    { name: "BeH₂", status: "active",   formula: "Beryllium Hydride",   qubits: "14 (tapered: 10)",note: "[4,4] active space" },
    { name: "H₂O",  status: "active",   formula: "Water",               qubits: "14 (tapered: 10)",note: "[4,4] active space" },
    { name: "NH₃",  status: "active",   formula: "Ammonia",             qubits: "14 (tapered: 10)",note: "[4,4] active space" },
    { name: "N₂",   status: "research", formula: "Nitrogen",            qubits: "24 (tapered: 18)",note: "[6,6] active space — research tier" },
  ];

  const encodings = [
    {
      name: "Jordan-Wigner (JW)",
      desc: "Maps fermionic operators to qubit operators preserving locality."
    },
    {
      name: "Bravyi-Kitaev (BK)",
      desc: "Balances locality and non-locality for efficient qubit mapping."
    },
    {
      name: "Parity",
      desc: "Encodes parity information, enabling qubit reduction techniques."
    }
  ];

  const ansatzTypes = [
    {
      name: "UCCSD",
      full: "Unitary Coupled Cluster Singles and Doubles",
      desc: "Chemically-inspired ansatz with high accuracy but deeper circuits."
    },
    {
      name: "HEA",
      full: "Hardware-Efficient Ansatz",
      desc: "Shallow circuits optimized for near-term hardware with reduced gate count."
    }
  ];

  return (
    <div className="container py-16 max-w-4xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-2">Benchmark Specification</h1>
      <p className="text-muted-foreground mb-2">QEncode uses fixed suite definitions so every managed run is reproducible and directly comparable.</p>
      <p className="text-xs text-muted-foreground mb-10">
        <span className="font-medium">Suite v3 pipeline:</span> PySCF CASCI (active-space FCI reference) → PennyLane molecular Hamiltonian → Z2 symmetry tapering → COBYLA VQE
      </p>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-1">Suite Molecules</h2>
        <p className="text-sm text-muted-foreground mb-4">Suite v3 — 7 molecules (6 certified + 1 research tier)</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {molecules.map((m) => (
            <div key={m.name} className="rounded-lg border bg-card p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-mono text-lg">{m.name}</h3>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    m.status === "active"
                      ? "bg-primary text-primary-foreground"
                      : m.status === "research"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  {m.status}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">{m.formula}</p>
              <p className="text-xs text-muted-foreground mt-1">{m.qubits} qubits</p>
              {m.note && <p className="text-xs text-muted-foreground/70 mt-0.5">{m.note}</p>}
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Encodings</h2>
        <div className="space-y-3">
          {encodings.map((e) => (
            <div key={e.name} className="rounded-lg border p-4">
              <h3 className="font-semibold text-sm mb-1">{e.name}</h3>
              <p className="text-sm text-muted-foreground">{e.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Ansatz Types</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {ansatzTypes.map((a) => (
            <div key={a.name} className="rounded-lg border bg-card p-5">
              <h3 className="font-mono text-lg mb-1">{a.name}</h3>
              <p className="text-xs text-muted-foreground mb-2">{a.full}</p>
              <p className="text-sm text-muted-foreground">{a.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-4">Reproducibility</h2>
        <div className="rounded-lg border p-6 bg-muted/30">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Every benchmark in QEncode uses a fixed configuration: molecule geometry, basis set, encoding, and ansatz are predetermined by suite rules. This eliminates variability across studies and ensures reproducible comparisons. Each result is tagged with a unique configuration string (e.g.,{" "}
            <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">qenc-h2-bk-uccsd-v1</code>) for unambiguous reference.
          </p>
        </div>
      </section>
      <section className="mt-8 rounded-lg border p-6">
        <h2 className="text-xl font-semibold mb-2">Access model</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          The benchmark specification is public, while managed execution, private benchmarking, and official certification
          are provided through access-approved plans. This keeps methodology transparent and operations production-grade.
        </p>
      </section>
    </div>
  );
}

