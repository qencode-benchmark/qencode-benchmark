export default function AboutPage() {
  return (
    <div className="container py-16 max-w-2xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-6">About QEncode</h1>
      <p className="text-lg text-muted-foreground leading-relaxed mb-6">
        QEncode is focused on building a standard benchmarking framework for quantum algorithms.
      </p>

      <p className="text-muted-foreground leading-relaxed mb-6">
        The quantum computing field lacks consistent benchmarking standards. Researchers evaluate algorithms using different molecules, encodings, and hardware configurations — making it nearly impossible to compare results across studies. QEncode addresses this by providing a fixed, open benchmark suite that anyone can run.
      </p>

      <p className="text-muted-foreground leading-relaxed mb-6">
        We believe that standardized evaluation is essential for meaningful progress in quantum algorithm development. By establishing clear benchmarks and a public leaderboard, we aim to accelerate the field and help researchers focus on what matters: building better algorithms.
      </p>

      <section className="rounded-lg border p-6 bg-muted/30">
        <h2 className="font-semibold mb-2">Vision</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          To become the accepted standard for quantum algorithm benchmarking — enabling fair comparison, reproducible science, and faster progress toward practical quantum advantage.
        </p>
      </section>

      <section className="rounded-lg border p-6 mt-4">
        <h2 className="font-semibold mb-2">Why this matters</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          The field lacks consistent benchmarking standards. QEncode addresses this with fixed suites,
          certified results, transparent scoring, and public datasets.
        </p>
      </section>
    </div>
  );
}

