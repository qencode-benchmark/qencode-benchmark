import Link from "next/link";

export const metadata = {
  title: "We Audited Our Own VQE Benchmark and Found the Numbers Were Partly Luck",
  description:
    "Threaded BLAS makes gradient-free VQE optimization non-deterministic. The same COBYLA command returned 8.99 and 0.53 mHa on identical hardware. We traced it, fixed it with one line, and re-ran all 46 entries. ADAPT-VQE with analytic gradients was never affected.",
  alternates: { canonical: "/blog/vqe-reproducibility-threading-bug" },
  openGraph: {
    title: "We Audited Our Own VQE Benchmark and Found the Numbers Were Partly Luck",
    description:
      "Identical command, identical seed, identical software: 8.99 mHa or 0.53 mHa depending on CPU core count. Why threaded BLAS breaks COBYLA reproducibility — and why ADAPT-VQE is immune.",
    url: "https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug",
    type: "article",
  },
};

const articleSchema = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: "We Audited Our Own VQE Benchmark and Found the Numbers Were Partly Luck",
  description:
    "Threaded BLAS makes gradient-free VQE optimization non-deterministic. The same COBYLA command returned 8.99 and 0.53 mHa on identical hardware. Setting OMP_NUM_THREADS=1 restores bit-for-bit reproducibility. ADAPT-VQE with analytic gradients was unaffected.",
  datePublished: "2026-07-16",
  dateModified: "2026-07-16",
  author: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  publisher: { "@type": "Organization", name: "QEncode", url: "https://www.qencode-benchmark.org" },
  url: "https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug",
  keywords: [
    "VQE reproducibility", "OMP_NUM_THREADS", "threaded BLAS non-determinism",
    "COBYLA optimizer", "ADAPT-VQE", "floating point associativity",
    "quantum chemistry benchmark", "H10 hydrogen chain", "variational quantum eigensolver",
    "local minima", "reproducible quantum computing", "QEncode v4.4",
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
      name: "Why do VQE calculations give different results on each run?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Threaded BLAS libraries sum floating-point numbers in whatever order CPU cores finish. Floating-point addition is not associative, so the energy changes in its final bits. Gradient-free optimizers such as COBYLA choose their next step by comparing energies, so that noise decides the direction whenever two candidates are close. One different step early sends the optimizer into a different local minimum. Setting OMP_NUM_THREADS=1 makes the summation order fixed and the result bit-for-bit reproducible.",
      },
    },
    {
      "@type": "Question",
      name: "Does OMP_NUM_THREADS affect VQE results?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes, when the optimizer is gradient-free. In a measured example (LiH, parity mapping, hardware-efficient ansatz, 10 restarts, seed 42), the identical command returned 5.18 mHa at one thread and 8.99 or 0.53 mHa at four threads depending only on machine load. At OMP_NUM_THREADS=1 the same command returned 5.181379e-03 Ha three times in a row, identical to the last digit.",
      },
    },
    {
      "@type": "Question",
      name: "Is ADAPT-VQE reproducible under multi-threaded BLAS?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "ADAPT-VQE driven by analytic gradients is effectively immune. Gradient-based optimizers compute a search direction rather than comparing noisy energy samples. Measured on H8 (16 qubits, statevector engine with L-BFGS-B), single-threaded and multi-threaded runs returned identical energy (-4.4047495716 Ha), identical operator count (98), and identical evaluation count (nfev 63072). Gradient-free COBYLA on the same hardware varied by a factor of 17.",
      },
    },
    {
      "@type": "Question",
      name: "How many ADAPT-VQE operators does an H10 hydrogen chain need?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "300 operators to reach a 9.977 mHa gap against the CASCI reference for H10 at cc-pVDZ with a [10e,10o] active space, 20 qubits tapered to 18. The measured series is H6: 28 operators, H8: 98, H10: 300 — roughly 3.2x per two added orbitals, consistent with exponential scaling in system size.",
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
          <time dateTime="2026-07-16">July 16, 2026</time>
          <span>·</span>
          <span>11 min read</span>
          <span>·</span>
          <span>QEncode Team</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground leading-snug">
          We Audited Our Own VQE Benchmark and Found the Numbers Were Partly Luck
        </h1>
        <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
          We set out to certify H₁₀ — a ten-atom hydrogen chain, 20 qubits, the largest
          system on the QEncode leaderboard. We got it: 9.977 mHa, 300 operators. But on
          the way we found something that mattered more. Run the same command twice and
          our benchmark returned different answers. Not because of a bug in our code, and
          not because of a version mismatch. Because of how a CPU adds numbers.
        </p>
      </div>

      <div className="prose prose-neutral dark:prose-invert max-w-none text-[15px] leading-7 text-foreground/90 space-y-6">

        <div className="rounded-lg border bg-muted/40 p-5 not-prose">
          <p className="text-sm font-semibold text-foreground mb-2">The short version</p>
          <p className="text-sm text-muted-foreground leading-6">
            Threaded BLAS sums floating-point numbers in nondeterministic order. That perturbs
            VQE energies in their last bits. Gradient-free optimizers like COBYLA choose their
            next step by <em>comparing</em> energies, so the noise picks the direction and the
            optimizer lands in a different local minimum. The same LiH command returned{" "}
            <strong>8.99 mHa or 0.53 mHa</strong> depending on nothing but CPU load.{" "}
            <strong>OMP_NUM_THREADS=1</strong> makes it bit-for-bit reproducible. ADAPT-VQE with
            analytic gradients was never affected.
          </p>
        </div>

        <h2 className="text-xl font-semibold mt-8 mb-3">The number that would not sit still</h2>

        <p>
          It started with a single entry that refused to reproduce. Our H₆ hydrogen chain was
          published at a 9.755 mHa gap. Re-running it gave 9.273 mHa. Same molecule, same
          config, same seed.
        </p>

        <p>
          The obvious suspect was a code change — we had recently switched ADAPT-VQE to
          commutator gradients. We checked out the old commit and re-ran. Still 9.273. So the
          code was innocent.
        </p>

        <p>
          The second suspect was the environment. Our{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">requirements-v4.txt</code>{" "}
          pinned PennyLane 0.45.0, NumPy 2.2.6, PySCF 2.6.2, SciPy 1.13.1 — and both our
          machines had quietly drifted to PennyLane 0.44.1, NumPy 1.26.4, PySCF 2.5.0, SciPy
          1.17.0. Twenty-one of our forty-six entries had been produced on an unpinned stack.
          That looked like the answer. We rebuilt the environment from the pin, re-ran, and got
          9.755 — matching the published value.
        </p>

        <p>
          Case closed. Except it was wrong.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Two samples of a coin flip</h2>

        <p>
          We had run each environment exactly once, got one number from each, and constructed a
          causal story out of it. When we ran the <em>same</em> environment repeatedly, both
          numbers appeared:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            H₆ JW/ADAPT — identical command, identical stack, identical seed
          </p>
          <p>OMP_NUM_THREADS=4, run 1 →  9.755353e-03 Ha</p>
          <p>OMP_NUM_THREADS=4, run 2 →  9.272866e-03 Ha</p>
        </div>

        <p>
          Both "environments" had been giving us random draws from the same distribution. The
          9.755 we had chased for hours was a coin flip that came up heads.
        </p>

        <p>
          The real variable was the thread count. Pin it, and the noise vanishes:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            LiH PAR/HEA — identical command, only OMP_NUM_THREADS varying
          </p>
          <p>OMP_NUM_THREADS=1 →  5.181379e-03   5.181379e-03   5.181379e-03</p>
          <p>OMP_NUM_THREADS=4 →  8.993703e-03   5.309440e-04   8.993703e-03</p>
        </div>

        <p>
          A seventeen-fold spread at four threads, and not even stable at a fixed thread count —
          it depended on how busy the machine was. At one thread: identical to the last digit,
          every time.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The decisive test</h2>

        <p>
          If threading was the cause, then two completely different software stacks should agree
          once threading is pinned. We ran H₆ at one thread on both:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p>PL 0.45.0 / numpy 2.2.6 / pyscf 2.6.2 / scipy 1.13.1</p>
          <p className="text-foreground">   → -3.3075959902 Ha   (nfev 6023)</p>
          <p className="mt-2">PL 0.44.1 / numpy 1.26.4 / pyscf 2.5.0 / scipy 1.17.0</p>
          <p className="text-foreground">   → -3.3075960058 Ha   (nfev 5678)</p>
        </div>

        <p>
          Different PennyLane, different NumPy, different PySCF, different SciPy — agreement to
          seven decimal places. SciPy's COBYLA rewrite changes <em>how many</em> evaluations it
          takes (6023 versus 5678) but not <em>where it lands</em>. The environments never
          mattered. The threads did.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why this happens</h2>

        <p>
          Floating-point addition is not associative. <code className="font-mono text-xs bg-muted px-1 rounded">(a+b)+c</code>{" "}
          and <code className="font-mono text-xs bg-muted px-1 rounded">a+(b+c)</code> can differ
          in the last bits. A threaded BLAS library splits a sum across cores and combines the
          partial results in whatever order the threads finish — which depends on scheduling,
          cache state, and what else the machine is doing. So the same energy evaluation returns
          values that differ at roughly 1e-16.
        </p>

        <p>
          That is normally harmless. It stops being harmless when an optimizer uses those values
          to make decisions.
        </p>

        <p>
          <strong>COBYLA is gradient-free.</strong> It has no derivative to follow, so it decides
          where to step by comparing sampled energies. When two candidate directions are nearly
          tied, a 1e-16 difference chooses between them. One different choice early in the run
          sends the optimizer down a different branch — and the hardware-efficient ansatz has a
          famously multi-modal landscape, full of local minima. The two branches end in different
          valleys. Hence 0.53 versus 8.99 mHa from the same command.
        </p>

        <p>
          <strong>Gradient-based optimizers do not have this problem.</strong> L-BFGS-B and our
          statevector ADAPT engine compute a search direction from analytic gradients rather than
          inferring one from noisy comparisons. A perturbation at 1e-16 moves the computed
          direction by 1e-16 — it does not flip a decision.
        </p>

        <p>
          That prediction is testable, and it held. H₈, run through the statevector engine with
          L-BFGS-B:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p>single-threaded  → -4.4047495716 Ha   98 ops   nfev 63072</p>
          <p>multi-threaded   → -4.4047495716 Ha   98 ops   nfev 63072</p>
        </div>

        <p>
          Identical energy, identical operator count, identical evaluation count. The distinction
          is not "VQE is irreproducible" — it is specifically{" "}
          <strong>gradient-free optimization on a multi-modal landscape with nondeterministic
          arithmetic</strong>.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What it meant for our published numbers</h2>

        <p>
          This is the uncomfortable part. Our entries were real VQE runs — nothing was fabricated
          — but several were lucky draws rather than the value the configuration actually converges
          to. Re-running everything deterministically moved them:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            published → deterministic (mHa)
          </p>
          <p>N₂   JW/UCCSD    2.016 → 10.832   (lost certification)</p>
          <p>NH₃  PAR/HEA     0.369 → 6.911</p>
          <p>LiH  PAR/HEA     0.410 → 5.181</p>
          <p>BeH₂ PAR/UCCSD   0.003 → 2.223</p>
          <p>H₄   JW/UCCSD    0.132 → 2.222</p>
          <p>H₆   JW/ADAPT    9.755 → 9.273</p>
          <p className="mt-2 text-muted-foreground">and some improved:</p>
          <p>N₂   PAR/HEA     14.261 → 9.504   (gained certification)</p>
          <p>H₂O  JW/HEA       0.084 → 0.000</p>
          <p>NH₃  JW/UCCSD     0.244 → 0.032</p>
        </div>

        <p>
          The suite total is unchanged — 39 certified entries across 14 molecules — but that is
          partly coincidence and we would rather say so. Two entries crossed the threshold in
          opposite directions and cancelled out. N₂ JW/UCCSD, our 404-parameter run, was published
          at 2.016 mHa; its deterministic value is 10.832 mHa, just over the 10 mHa line, so it is
          now research tier. N₂ PAR/HEA went the other way, from 14.261 to 9.504, and is now
          certified. N₂ remains certified as a molecule through its ADAPT and JW/HEA entries.
        </p>

        <p>
          The 2.016 mHa was a real run. It was also a lucky one. Losing it is the honest cost of
          this exercise, and it is worth more than keeping it would have been.
        </p>

        <p>
          We verified the new values are actually reproducible rather than assuming it. We picked
          the four entries that moved <em>most</em> — the most fragile cases — and re-ran them:
          BeH₂ 2.222518, LiH 5.181379, NH₃ 6.911462, H₄ 2.221795. All bit-identical to the
          recorded values.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">The fix</h2>

        <p>
          One line, with one subtlety: the thread limits must be set <em>before</em> NumPy is
          imported. After that, BLAS has already built its thread pool and the variables are
          silently ignored.
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="text-muted-foreground"># at the very top of the module, before `import numpy`</p>
          <p>for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",</p>
          <p>{"          "}"NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):</p>
          <p>{"    "}os.environ[v] = "1"</p>
        </div>

        <p>
          We also made this a property of the entry rather than of whoever ran it. The pipeline
          now refuses to write a certified entry unless BLAS is single-threaded, the git tree is
          clean (so the recorded commit actually describes the running code), and every pin in{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">requirements-v4.txt</code>{" "}
          matches what is importable. Each entry records{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">blas_threads</code> in its
          provenance.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">Suite v4.4: one commit, one stack, one method</h2>

        <p>
          We regenerated all 46 entries. The suite went from a patchwork to something uniform:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">before → after</p>
          <p>git commits          11 → 1</p>
          <p>PennyLane versions    2 → 1</p>
          <p>Hamiltonian paths     2 → 1  (and now recorded)</p>
          <p>BLAS threads    variable → 1</p>
          <p>certified entries    39 → 39</p>
        </div>

        <p>
          The Hamiltonian path deserves its own mention. We had been silently running two: 25
          entries built the qubit Hamiltonian from PySCF integrals via OpenFermion, and 19 used
          PennyLane's native <code className="font-mono text-xs bg-muted px-1 rounded">molecular_hamiltonian</code>,
          which runs its own Hartree-Fock and lands on a slightly different active space. The
          exact ground state of those Hamiltonians sat up to 3.6e-4 Ha from the CASCI energy the
          entries claimed to target, versus ~1e-15 Ha for the OpenFermion path. Nothing recorded
          which path an entry had used — we had to infer it from that energy fingerprint. The
          integral-based path is now the default, and{" "}
          <code className="font-mono text-xs bg-muted px-1 rounded">hamiltonian_source</code> is
          recorded per entry.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">And H₁₀, since you asked</h2>

        <p>
          H₁₀ certified at <strong>9.977 mHa with 300 operators</strong> — a [10e,10o] active
          space, 20 qubits tapered to 18, 14,227 Pauli terms, CASSCF orbitals. It is the largest
          certified system on the leaderboard.
        </p>

        <p>
          Multi-threaded, H₁₀ returned 300, 200, then 300 operators across three runs. Single
          threaded it returns 300 every time. That matters, because the operator count is the
          interesting number:
        </p>

        <div className="rounded-md bg-muted p-4 text-xs font-mono leading-6 not-prose overflow-x-auto">
          <p className="font-sans text-sm font-semibold text-foreground mb-2">
            ADAPT operators to reach the 10 mHa threshold (cc-pVDZ)
          </p>
          <p>H₆   [6e,6o]    12 → 9 qubits     28 operators</p>
          <p>H₈   [8e,8o]    16 → 13 qubits    98 operators     (3.5×)</p>
          <p>H₁₀  [10e,10o]  20 → 18 qubits   300 operators     (3.1×)</p>
        </div>

        <p>
          Roughly 3.2× per two added orbitals. That is exponential growth in the ansatz size, and
          it is consistent with recent work arguing that ADAPT-VQE parameter counts scale
          exponentially with system size. Those analyses generally report the trend without
          publishing per-molecule operator counts at a fixed accuracy threshold. Ours are above,
          and the full entries — including every selected operator index and the serialized
          Hamiltonian — are downloadable, so the numbers can be checked rather than taken on
          trust.
        </p>

        <p>
          One caveat we will not paper over: these counts are at our 10 mHa certification
          threshold, not at the 1.6 mHa chemical-accuracy threshold used elsewhere. Tighter
          thresholds need more operators. The scaling is the point, not the absolute values.
        </p>

        <h2 className="text-xl font-semibold mt-8 mb-3">What this means if you run VQE</h2>

        <p>
          Threaded BLAS is on by default nearly everywhere. NumPy, SciPy, PennyLane and PySCF will
          happily use every core you have. If your optimizer is gradient-free — COBYLA,
          Nelder-Mead, Powell — and your ansatz landscape is multi-modal, your published number
          may be a sample rather than a result. It costs one afternoon to check: run the same
          configuration three times and see whether the digits agree.
        </p>

        <p>Concretely:</p>

        <ul className="list-disc pl-6 space-y-1">
          <li>
            Set <code className="font-mono text-xs bg-muted px-1 rounded">OMP_NUM_THREADS=1</code>{" "}
            before importing NumPy, and record it alongside your package versions.
          </li>
          <li>
            Prefer gradient-based optimizers where you can. Beyond the reproducibility argument,
            L-BFGS-B was roughly 20× faster than COBYLA in our H₁₀ runs and reached the same
            energies.
          </li>
          <li>
            If you must use a gradient-free optimizer, report a distribution rather than a single
            value — or pin your threads and say so.
          </li>
        </ul>

        <h2 className="text-xl font-semibold mt-8 mb-3">Why we published this</h2>

        <p>
          It would have been easy not to. The bug was invisible, no one had complained, and the
          fix quietly makes several of our headline numbers worse. We could have re-run everything
          and said nothing.
        </p>

        <p>
          But a benchmark that has never reported bad news about itself is not a benchmark anyone
          should trust. We pin package versions, hash every entry with SHA-256, and sign certified
          results with Ed25519 — and underneath all of that, the arithmetic was rolling dice. A
          user could match our commit, match our stack, run our exact command, and legitimately
          get a different answer because their CPU had a different core count. That is precisely
          the failure this project exists to prevent.
        </p>

        <p>
          The whole point of the checks we found this with is that they were written down{" "}
          <em>before</em> we looked. We predicted that the 25 already-correct entries should come
          back identical; they did not, and that is what exposed a bug in our own re-run script.
          A benchmark should be the thing that catches this, including when the thing it catches
          is itself.
        </p>

        <div className="rounded-lg border bg-muted/40 p-5 not-prose mt-8">
          <p className="text-sm font-semibold text-foreground mb-2">Check it yourself</p>
          <p className="text-sm text-muted-foreground leading-6 mb-3">
            Every Suite v4.4 entry — energies, run config, provenance, the serialized Hamiltonian,
            and every selected ADAPT operator — is in the public repository. The reproducibility
            guard is in{" "}
            <code className="font-mono text-xs bg-background px-1 rounded">scripts/generate_entry_v4.py</code>.
          </p>
          <div className="text-sm space-x-4">
            <Link href="/leaderboard" className="text-primary hover:underline">
              View the leaderboard →
            </Link>
            <Link href="/methodology" className="text-primary hover:underline">
              Read the methodology →
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
