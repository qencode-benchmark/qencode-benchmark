import Link from "next/link";

export const metadata = {
  title: "The Four Things That Make a VQE Result Reproducible",
  description:
    "Reproducibility is not one property — it is four: deterministic arithmetic, recorded package versions, a recorded seed, and a recorded code version. Setting a random seed fixes none of the hardest one. A free scorecard checks your setup and prints the fix.",
  alternates: { canonical: "/blog/vqe-reproducibility-scorecard" },
  openGraph: {
    title: "The Four Things That Make a VQE Result Reproducible",
    description:
      "Deterministic arithmetic, recorded versions, a recorded seed, a recorded commit. A free tool (NumPy + SciPy only) checks all four on your own machine and shows the one-line fix.",
    url: "https://www.qencode-benchmark.org/blog/vqe-reproducibility-scorecard",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "The Four Things That Make a VQE Result Reproducible",
  description:
    "A VQE result is reproducible only when four conditions hold: single-threaded BLAS for deterministic arithmetic, recorded package versions, a recorded random seed, and a recorded code version. QEncode publishes a free scorecard that checks all four.",
  datePublished: "2026-07-28",
  dateModified: "2026-07-28",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/vqe-reproducibility-scorecard",
  keywords: [
    "VQE reproducibility", "reproducibility checklist", "reproducibility scorecard",
    "OMP_NUM_THREADS", "threaded BLAS", "random seed", "package pinning",
    "quantum chemistry benchmark", "variational quantum eigensolver", "COBYLA",
    "computational reproducibility", "QEncode",
  ],
};

// Answer-first blocks: written to be quotable in isolation by search and by
// language models, which lift short factual passages rather than whole articles.
const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What makes a VQE result reproducible?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Four conditions. (1) Deterministic arithmetic: set OMP_NUM_THREADS=1 before importing NumPy so threaded BLAS does not sum floating-point numbers in a nondeterministic order. (2) Recorded package versions: pin numpy, scipy and your quantum libraries so another machine can rebuild the exact stack. (3) A recorded random seed: set one and write it down. (4) A recorded code version: commit your code so the exact version that produced a result can be recovered. The first condition is about the arithmetic; the other three are about record-keeping. Miss any one and the number cannot be independently reproduced.",
      },
    },
    {
      "@type": "Question",
      name: "Does setting a random seed make a VQE calculation reproducible?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No, not by itself. A seed fixes the random draws in your own code, but the largest source of run-to-run variation in gradient-free VQE is threaded BLAS, which sums floating-point numbers in whatever order the CPU cores finish. That is arithmetic non-determinism, not randomness, and no seed controls it. You must also set OMP_NUM_THREADS=1 before NumPy is imported. A seed is necessary but not sufficient.",
      },
    },
    {
      "@type": "Question",
      name: "How can I check whether my VQE result is reproducible?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Two ways. Quickly: run the identical configuration three times and check whether the digits agree; if they drift, your setup is non-deterministic. Systematically: run a reproducibility scorecard that inspects your environment. QEncode publishes a free one, tools/check_vqe_reproducibility.py, which needs only NumPy and SciPy and reports whether your BLAS is single-threaded, whether your package versions are recorded, and whether your code is committed, then prints the one-line fix when it finds a problem.",
      },
    },
    {
      "@type": "Question",
      name: "What is a reproducibility scorecard?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "A checklist of the conditions a computational result needs in order to be reproduced by someone else, applied automatically to your environment: deterministic arithmetic, recorded package versions, a recorded random seed, and a recorded code version. It reports which conditions your current setup meets and which are at risk. For VQE the decisive one is single-threaded BLAS, because gradient-free optimizers turn last-bit arithmetic noise into different local minima.",
      },
    },
  ],
};

export default function Post() {
  return (
    <main className="container max-w-2xl py-16">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(articleSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
        ← Blog
      </Link>

      <div className="mt-8 mb-10">
        <div className="flex items-center gap-3 text-xs text-muted-foreground mb-4">
          <time dateTime="2026-07-28">July 28, 2026</time>
          <span>·</span>
          <span>6 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          The Four Things That Make a VQE Result Reproducible
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          Two weeks ago we{" "}
          <Link href="/blog/vqe-reproducibility-threading-bug" className="text-primary hover:underline">
            found that some of our own published numbers were partly luck
          </Link>{" "}
          — threaded arithmetic was quietly rolling dice underneath a gradient-free
          optimizer. Fixing it raised an obvious next question: what would we have needed
          to check <em>in advance</em> to know a result was reproducible? It turns out to
          be four things, not one. So we wrote them down, and built a small tool that
          checks them on your own code.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            A VQE number is reproducible only if four things are true: the arithmetic is{" "}
            <strong>deterministic</strong> (single-threaded BLAS), and the{" "}
            <strong>versions</strong>, the <strong>seed</strong>, and the{" "}
            <strong>code version</strong> are all recorded. One is about how the CPU adds
            numbers; three are about writing things down. Setting a random seed — the thing
            most people reach for first — fixes none of the hard one. We packaged all four
            into a free checker you can run in ten seconds:{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">python check_vqe_reproducibility.py</code>.
          </p>
        </div>

        <p>
          "Reproducible" gets used as though it were a single switch. It is not. A result
          reproduces when someone else — or you, six months later, on a different machine —
          can run the same thing and get the same number to the digits that matter. That
          requires the computation to be deterministic <em>and</em> the recipe to be fully
          written down. Those are separate failures, and most published VQE results miss at
          least one.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">1. Deterministic arithmetic</h2>

        <p>
          This is the one almost nobody checks, and it is the one that bit us. Threaded
          BLAS — the linear algebra under NumPy and SciPy — splits a sum across CPU cores
          and combines the partial results in whatever order the threads finish. Floating-point
          addition is not associative, so the answer changes in its last bits depending on
          core count and machine load. A gradient-free optimizer such as COBYLA, Nelder-Mead
          or Powell chooses its next step by <em>comparing</em> energies, so that 1e-16 noise
          decides the direction whenever two candidates are close — and on a multi-modal
          landscape one different step early lands you in a different local minimum. The
          same command returned{" "}
          <Link href="/blog/vqe-reproducibility-threading-bug" className="text-primary hover:underline">
            8.99 mHa or 0.53 mHa
          </Link>{" "}
          for us, depending on nothing but how busy the machine was.
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="text-muted-foreground"># the fix — before `import numpy`, not after</p>
          <p>import os</p>
          <p>for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",</p>
          <p>{"          "}"NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):</p>
          <p>{"    "}os.environ[v] = "1"</p>
          <p>import numpy as np   # everything after this is deterministic</p>
        </div>

        <p>
          Gradient-<em>based</em> optimizers (L-BFGS-B, and our statevector ADAPT engine)
          are effectively immune: a perturbation at 1e-16 moves the computed search
          direction by 1e-16, it does not flip a decision. If you can use analytic
          gradients, this whole problem mostly disappears — and in our runs L-BFGS-B was
          also roughly 20× faster than COBYLA.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">2. Recorded package versions</h2>

        <p>
          A result that only reproduces on your exact stack is not reproducible unless that
          stack is written down. VQE code sits on numpy, scipy, and a quantum library or two
          (PennyLane, Qiskit, OpenFermion, PySCF), and those move. During our own audit two
          of our machines had quietly drifted across four packages — one of them a whole
          major version — without anyone noticing. Pin them — a{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">requirements.txt</code>{" "}
          with <code className="font-mono text-xs bg-muted px-1 rounded">==</code> versions,
          or an <code className="font-mono text-xs bg-muted px-1 rounded">environment.yml</code>{" "}
          — and keep it next to the results.
        </p>

        <p>
          Worth saying plainly, because the story above makes it tempting to blame versions:
          a version drift changes <em>how many</em> optimizer steps you take, but pinned
          threads plus different NumPy still landed on the same energy to seven figures for
          us. Versions matter for reproducibility, but they were not the source of the
          non-determinism. Record them anyway — the next person cannot rebuild your run
          without them.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">3. A recorded random seed</h2>

        <p>
          Set a seed for every stochastic step — parameter initialization, any sampling —
          and record its value, not just the fact that you set one. This is the condition
          people reach for first, so here is the trap: <strong>a seed does not fix
          condition 1.</strong> It controls the random draws in <em>your</em> code; it does
          nothing about the order in which BLAS adds floats across threads. We have seen
          runs with a fixed seed still return a seventeen-fold spread, purely from threading.
          A seed is necessary. It is nowhere near sufficient.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">4. A recorded code version</h2>

        <p>
          The code that produced the number has to be recoverable. In practice that means a
          clean git commit: everything committed, and the commit hash stored with the result,
          so "the code that ran" is not "whatever was in my working directory that afternoon."
          An uncommitted change is invisible to anyone trying to reproduce you — including
          future you.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">A tool that checks all four</h2>

        <p>
          We already enforce these four inside our own pipeline: it refuses to write a
          certified entry unless BLAS is single-threaded, the git tree is clean, and every
          pin matches what is importable. We pulled that logic out into a standalone,
          dependency-light script — NumPy and SciPy only — so anyone can point it at their
          own setup:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p>$ python check_vqe_reproducibility.py</p>
          <p className="mt-2 text-muted-foreground">Determinism — what we can check for you</p>
          <p>{"  "}[✗] BLAS single-threaded</p>
          <p>{"      "}64 threads — AT RISK: gradient-free optimizers can</p>
          <p>{"      "}return different energies run to run. Seed does not help.</p>
          <p className="mt-2 text-muted-foreground">Provenance — what you must record</p>
          <p>{"  "}[i] exact versions ... numpy 1.26.4, scipy 1.17.0, pennylane 0.44.1</p>
          <p>{"  "}[?] random seed ...... can&#39;t see your code; set AND record one</p>
          <p>{"  "}[✓] code version ..... clean git tree @ a1b2c3d</p>
          <p className="mt-2">{"  "}Your arithmetic is NON-DETERMINISTIC.  Fix threads (below).</p>
        </div>

        <p>
          The verdict on threading is a hard yes/no — it reads your actual BLAS thread count
          — and it prints the exact fix if you are at risk. The three provenance checks are
          honest about their limits: it shows your installed versions and looks for a pin
          file, it reports your git state, and for the seed it simply reminds you, because it
          cannot read your code. It does not pretend to certify you; it tells you which of the
          four conditions it can see, and flags the rest.
        </p>

        <p>
          Add <code className="font-mono text-xs bg-muted px-1 rounded">--record</code> and
          it writes a small{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">qencode_reproducibility.json</code>{" "}
          — platform, thread count, every detected package version, and the git commit — a
          provenance receipt you can save alongside your results so the environment that
          produced them can be verified later. Add{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">--live</code> and it will
          attempt an actual reproduction (a small VQE at one thread versus many); it is
          candid that a quiet result is not a clean bill of health, because whether the
          failure surfaces depends on the BLAS build, core count, and load.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The ten-second version</h2>

        <p>
          If you run VQE and want one thing to do today: run the same configuration three
          times and look at whether the digits agree. If they drift, you have a determinism
          problem, and it is almost certainly threading. Then set{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">OMP_NUM_THREADS=1</code>{" "}
          before you import NumPy, pin your versions, record your seed and your commit — and
          you have all four.
        </p>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm font-semibold text-foreground mb-2">Run it on your own code</p>
          <p className="text-sm text-muted-foreground leading-6 mb-3">
            The checker is in the public repository at{" "}
            <code className="font-mono text-xs bg-background px-1 rounded">tools/check_vqe_reproducibility.py</code>.
            Free to use and share. The full story of how we found the threading problem in
            our own numbers is in the companion post.
          </p>
          <div className="text-sm space-x-4">
            <Link href="/blog/vqe-reproducibility-threading-bug" className="text-primary hover:underline">
              Read the finding →
            </Link>
            <Link href="/methodology" className="text-primary hover:underline">
              Our methodology →
            </Link>
            <a
              href="https://github.com/qencode-benchmark/qencode-benchmark"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              GitHub →
            </a>
          </div>
        </div>

      </div>
    </main>
  );
}
