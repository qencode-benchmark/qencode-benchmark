export const metadata = {
  title: "Benchmark Specification",
  description:
    "Review QEncode Standard Suite v2 benchmark specifications: molecules, qubit encodings, ansatz types, and reproducibility constraints for fair quantum algorithm comparison.",
  keywords: [
    "quantum benchmark specification",
    "suite v2",
    "VQE molecules",
    "Jordan-Wigner Bravyi-Kitaev Parity",
    "UCCSD HEA"
  ],
  alternates: {
    canonical: "/benchmark"
  },
  openGraph: {
    title: "QEncode Benchmark Specification - Suite v2",
    description:
      "Fixed benchmark definitions for molecules, encodings, ansatz settings, and reproducibility in quantum algorithm testing.",
    url: "/benchmark"
  }
};

export default function BenchmarkPage() {
  const molecules = [
    { name: "H₂", status: "active", formula: "Hydrogen", qubits: 4 },
    { name: "BeH₂", status: "active", formula: "Beryllium Hydride", qubits: 14 },
    { name: "LiH", status: "active", formula: "Lithium Hydride", qubits: 12 },
    { name: "HF", status: "active", formula: "Hydrogen Fluoride", qubits: 12 },
    { name: "N₂", status: "expanded", formula: "Nitrogen", qubits: "active-space dependent" }
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
      <p className="text-muted-foreground mb-10">QEncode uses fixed suite definitions so every managed run is reproducible and directly comparable.</p>

      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-4">Suite Molecules</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {molecules.map((m) => (
            <div key={m.name} className="rounded-lg border bg-card p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-mono text-lg">{m.name}</h3>
                <span
                  className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    m.status === "active"
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  {m.status}
                </span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">{m.formula}</p>
              <p className="text-xs text-muted-foreground mt-1">{m.qubits} qubits</p>
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

