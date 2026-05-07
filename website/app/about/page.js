export const metadata = {
  title: "About QEncode",
  description:
    "Learn how QEncode standardizes quantum algorithm benchmarking with fixed suites, managed execution, and certification-grade reproducibility controls.",
  keywords: [
    "about qencode",
    "quantum benchmark standard",
    "quantum algorithm certification",
    "reproducible quantum evaluation"
  ],
  alternates: {
    canonical: "/about"
  },
  openGraph: {
    title: "About QEncode - Quantum Benchmark Standard",
    description:
      "QEncode provides benchmark standards and trust infrastructure for reproducible quantum algorithm evaluation.",
    url: "/about"
  }
};

export default function AboutPage() {
  return (
    <div className="container py-16 max-w-2xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-6">About QEncode</h1>
      <p className="text-lg text-muted-foreground leading-relaxed mb-6">
        QEncode builds the benchmark standard and execution platform for reproducible quantum algorithm evaluation.
      </p>

      <p className="text-muted-foreground leading-relaxed mb-6">
        Quantum studies often use different molecules, encodings, ansatz settings, and assumptions, making results hard
        to compare across teams. QEncode addresses this with fixed benchmark suites, managed execution workflows, and
        certification-grade outputs.
      </p>

      <p className="text-muted-foreground leading-relaxed mb-6">
        We believe standardized evaluation is essential for meaningful progress. By combining transparent benchmark rules
        with operational trust controls (signed receipts, audited datasets), QEncode helps researchers and companies make
        claims that stand up to scrutiny.
      </p>

      <section className="rounded-lg border p-6 bg-muted/30">
        <h2 className="font-semibold mb-2">Vision</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          To become the accepted benchmark standard and trust infrastructure for quantum algorithm performance.
        </p>
      </section>

      <section className="rounded-lg border p-6 mt-4">
        <h2 className="font-semibold mb-2">Platform model</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          QEncode keeps benchmark methodology public while monetizing managed execution, private benchmarking workflows,
          and official certification services.
        </p>
      </section>
    </div>
  );
}

