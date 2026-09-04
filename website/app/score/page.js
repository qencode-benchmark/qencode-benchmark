import Link from "next/link";
import { ArrowRight, CheckCircle, AlertTriangle, ExternalLink, Github, Package, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { scorableMolecules, referenceStats } from "@/lib/references";

const REPO = "https://github.com/qencode-benchmark/qencode-benchmark";
const PYPI = "https://pypi.org/project/qencode-benchmark/";
const NOTEBOOK = `${REPO}/blob/HEAD/notebooks/score_your_vqe_result.ipynb`;

export const metadata = {
  title: "Score Your VQE Result",
  description:
    "Score a VQE energy you computed yourself against the QEncode reference in one line. Reports the gap to the exact active-space ground state, the certification margin, and whether your optimiser and ansatz make that margin fragile. No chemistry stack required.",
  keywords: [
    "score VQE result",
    "VQE accuracy check",
    "compare VQE energy",
    "CASCI reference energy",
    "quantum chemistry benchmark python package",
    "qencode.score",
  ],
  alternates: { canonical: "/score" },
  openGraph: {
    title: "Score Your VQE Result — QEncode",
    description:
      "You have a VQE energy. Is it any good? One function call gives you the gap to the exact ground state, the certification margin, and whether that margin survives another machine.",
    url: "https://www.qencode-benchmark.org/score",
    type: "article",
  },
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "How do I check whether my VQE energy is accurate?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Compare it against the exact ground state of the same active-space Hamiltonian, obtained by exact diagonalisation (CASCI). QEncode ships those reference energies for all 16 suite molecules inside its Python package, so `pip install qencode-benchmark` then `qencode.score(energy, molecule=...)` returns the gap without you computing a CASCI reference yourself. The comparison is only meaningful when the molecule, geometry, basis, charge, spin and active space match the reference, which the function checks rather than assumes.",
      },
    },
    {
      "@type": "Question",
      name: "Does scoring a VQE result require PySCF or PennyLane?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No. The reference energies ship as a small JSON table inside the package, so scoring imports no chemistry stack and no NumPy. Generating a new benchmark entry does require the chemistry stack, because it computes the CASCI reference and runs the VQE, but scoring an energy you already have does not.",
      },
    },
    {
      "@type": "Question",
      name: "Does meeting the 10 mHa threshold mean my result is certified by QEncode?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "No. Scoring tells you a self-reported number would meet the threshold. Certification is what the pipeline produces: a full run with the environment pinned, the procedure and package versions recorded, a SHA-256 content hash over the result and an Ed25519 signature. A score is a measurement of a number you supplied; certification is a statement about a run that can be independently rebuilt.",
      },
    },
    {
      "@type": "Question",
      name: "Why does my optimiser and ansatz affect whether the result is trustworthy?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "A gradient-free optimiser such as COBYLA chooses its next step by comparing two nearly equal energies, so a difference in the thirteenth decimal — a different BLAS library, a different NumPy version — can flip a comparison and send the run into a different local minimum. But the optimiser alone is not the rule. Measured on H4, holding molecule, basis, mapping and environment fixed and changing only the ansatz, ADAPT-VQE with a COBYLA inner optimiser moved 3.4e-08 Ha across environments while a hardware-efficient ansatz under plain COBYLA moved 8.8e-04 Ha, a factor of about 25,595. ADAPT selects its operators by analytic gradient, so its structure is gradient-determined. The risk is the conjunction: a gradient-free optimiser on an unstructured ansatz.",
      },
    },
  ],
};

function Step({ n, children }) {
  return (
    <div className="flex gap-4">
      <span className="font-mono text-sm font-bold text-primary/40 shrink-0 pt-0.5">{n}</span>
      <div className="text-sm text-muted-foreground leading-relaxed">{children}</div>
    </div>
  );
}

export default function ScorePage() {
  const molecules = scorableMolecules();
  const stats = referenceStats();

  return (
    <div className="pb-4">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />

      {/* ── Hero ── */}
      <section className="container pt-12 pb-12 sm:pt-16 max-w-3xl">
        <div className="flex flex-wrap gap-2 mb-5">
          <Badge variant="secondary" className="text-xs font-mono">qencode-benchmark 4.5.0</Badge>
          <Badge variant="secondary" className="text-xs">No chemistry stack</Badge>
          <Badge variant="secondary" className="text-xs">{stats.molecules} molecules</Badge>
        </div>

        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight leading-[1.15] mb-5">
          You have a VQE energy. Is it any good?
        </h1>
        <p className="text-lg text-muted-foreground mb-4">
          Answering that means comparing it against the <em>exact</em> ground state of the same
          active-space Hamiltonian — and computing one normally costs a PySCF install and a wait.
        </p>
        <p className="text-base text-muted-foreground mb-8">
          QEncode ships those reference energies for all {stats.molecules} suite molecules inside
          the package. Scoring is one function call, imports no chemistry stack, and needs no
          network.
        </p>

        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <a href={NOTEBOOK} target="_blank" rel="noopener noreferrer" data-track="score_notebook">
              <BookOpen className="mr-1.5 h-4 w-4" /> Open the notebook
            </a>
          </Button>
          <Button asChild variant="secondary" size="lg">
            <a href={PYPI} target="_blank" rel="noopener noreferrer" data-track="score_pypi">
              <Package className="mr-1.5 h-4 w-4" /> View on PyPI
            </a>
          </Button>
          <Button asChild variant="outline" size="lg">
            <a href={REPO} target="_blank" rel="noopener noreferrer" data-track="score_github">
              <Github className="mr-1.5 h-4 w-4" /> Source
            </a>
          </Button>
        </div>
      </section>

      {/* ── The two-step ── */}
      <section className="border-y bg-muted/40">
        <div className="container py-12 max-w-3xl">
          <h2 className="text-xl font-semibold mb-5">Two steps</h2>

          <pre className="bg-background border rounded-md p-4 text-xs sm:text-sm font-mono overflow-x-auto leading-relaxed mb-4">
{`pip install qencode-benchmark`}
          </pre>

          <pre className="bg-background border rounded-md p-4 text-xs sm:text-sm font-mono overflow-x-auto leading-relaxed mb-6">
{`import qencode

s = qencode.score(-7.9835,               # your energy, in Hartree
                  molecule="LiH",
                  active_space=(4, 4),   # checked, not assumed
                  optimizer="COBYLA",
                  ansatz="hea")
print(s.report())`}
          </pre>

          <p className="text-sm text-muted-foreground mb-3">Which prints:</p>
          <pre className="bg-background border rounded-md p-4 text-[11px] sm:text-xs font-mono overflow-x-auto leading-relaxed">
{`  your energy             -7.9835000000 Ha
  exact ground state      -7.9837729770 Ha   (CASCI in the declared active space)
  gap                      0.0002729770 Ha   = 0.273 mHa

  reaches CHEMICAL ACCURACY (< 1.6 mHa) and would meet the 10 mHa certification threshold
  margin             9.727e-03 Ha (97.3% of the threshold)

  optimiser          COBYLA (gradient-free)
  amplifying         YES -- gradient-free optimiser on an unstructured
                     ansatz. Re-run elsewhere, energies in this class
                     have moved by up to 1e-2 Ha.

  among published    #3 of 4 QEncode entries for this problem
  best published gap 0.003 mHa`}
          </pre>
        </div>
      </section>

      {/* ── What it tells you ── */}
      <section className="container py-14 max-w-3xl">
        <h2 className="text-xl font-semibold mb-6">What the five numbers mean</h2>
        <div className="space-y-5">
          <Step n="01">
            <strong className="text-foreground">The gap.</strong> The distance from your energy to
            exact diagonalisation of the <em>same</em> active-space Hamiltonian. Not to experiment,
            and not to a complete-basis limit — those errors are shared by every method solving the
            same problem, so removing them isolates what the algorithm is responsible for.
          </Step>
          <Step n="02">
            <strong className="text-foreground">The tier.</strong> Chemical accuracy is 1.6 mHa
            (1 kcal/mol) — roughly where a computed reaction energy becomes useful to a chemist.
            The QEncode certification threshold is a deliberately looser 10 mHa, so an entry can be
            a well-executed reproducible calculation without also being chemically useful.
          </Step>
          <Step n="03">
            <strong className="text-foreground">The margin.</strong> 10 mHa minus your gap: how far
            the energy can move before the result stops meeting the threshold. Below 20% of the
            threshold is thin.
          </Step>
          <Step n="04">
            <strong className="text-foreground">Whether it will move.</strong> Margin bounds how far
            a result <em>can</em> drift; it says nothing about how far it <em>will</em>. That
            depends on your optimiser and ansatz — see below.
          </Step>
          <Step n="05">
            <strong className="text-foreground">Where it ranks.</strong> Against the published
            QEncode entries for the same problem. Gaps are comparable within a molecule and never
            across molecules.
          </Step>
        </div>
      </section>

      {/* ── The fragility finding ── */}
      <section className="border-t bg-muted/40">
        <div className="container py-14 max-w-3xl">
          <h2 className="text-xl font-semibold mb-4">
            The part you cannot get anywhere else
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed mb-4">
            A gradient-free optimiser picks its next step by comparing two nearly equal energies, so
            a difference in the thirteenth decimal — a different BLAS, a different NumPy — can flip
            a comparison and send the run into a different local minimum. That much is known.
          </p>
          <p className="text-sm text-muted-foreground leading-relaxed mb-5">
            What we measured is that <strong className="text-foreground">the optimiser alone is not
            the rule</strong>. Holding molecule, basis, mapping and environment fixed on H₄ and
            changing only the ansatz:
          </p>

          <div className="rounded-lg border bg-background overflow-hidden mb-5">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="text-left font-medium px-4 py-2.5">H₄ entry</th>
                  <th className="text-left font-medium px-4 py-2.5">Optimiser</th>
                  <th className="text-right font-medium px-4 py-2.5">Energy moved</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t">
                  <td className="px-4 py-2.5 font-mono text-xs">ADAPT</td>
                  <td className="px-4 py-2.5 text-muted-foreground">COBYLA <em>inner</em></td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs">3.4 × 10⁻⁸ Ha</td>
                </tr>
                <tr className="border-t">
                  <td className="px-4 py-2.5 font-mono text-xs">HEA</td>
                  <td className="px-4 py-2.5 text-muted-foreground">plain COBYLA</td>
                  <td className="px-4 py-2.5 text-right font-mono text-xs">8.8 × 10⁻⁴ Ha</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed">
            A factor of <strong className="text-foreground">25,595</strong>, with the same optimiser
            family on both rows. ADAPT-VQE selects its operators by analytic gradient, so the ansatz
            structure is gradient-determined and the gradient-free optimiser only polishes a small,
            well-conditioned parameter set. An unstructured ansatz hands the same optimiser a
            landscape full of near-degenerate minima. The risk is the <em>conjunction</em>:
            gradient-free <strong className="text-foreground">and</strong> unstructured — which is
            what the <code className="font-mono text-xs bg-muted px-1 rounded">amplifying</code> flag
            reports.
          </p>
        </div>
      </section>

      {/* ── Refusals ── */}
      <section className="container py-14 max-w-3xl">
        <h2 className="text-xl font-semibold mb-3">What it refuses to do</h2>
        <p className="text-sm text-muted-foreground mb-6">
          A scoring tool that always returns a number is easy to write and easy to mislead yourself
          with. These are the cases where it raises or warns instead.
        </p>

        <div className="space-y-4">
          {[
            {
              title: "A mismatched active space raises",
              body: "Declare an active space that differs from the reference and it raises rather than scoring. A gap measured between two different problems is not a worse number — it is a meaningless one.",
            },
            {
              title: "An energy below the variational minimum is reported first",
              body: "The variational principle forbids a wavefunction energy below the exact ground state. If yours is lower, the problem you solved is not the one you think — a different geometry, active space, charge or spin, or a Hamiltonian missing its nuclear repulsion. That warning comes before any gap.",
            },
            {
              title: "Nothing is ever called certified",
              body: "Scoring says a self-reported number would meet the threshold. Certification requires the pipeline: pinned environment, recorded provenance, a SHA-256 content hash and an Ed25519 signature. There is no field named certified, and a test enforces the wording.",
            },
            {
              title: "An unknown molecule raises, with the list",
              body: "Only the 16 suite molecules have published references. Anything else raises and tells you what is available, rather than silently comparing against the closest match.",
            },
          ].map((r) => (
            <div key={r.title} className="rounded-lg border p-5">
              <div className="flex items-start gap-2.5 mb-1.5">
                <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <h3 className="text-sm font-semibold text-foreground">{r.title}</h3>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed pl-6.5">{r.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Scorable molecules ── */}
      <section className="border-t bg-muted/40">
        <div className="container py-14 max-w-3xl">
          <h2 className="text-xl font-semibold mb-3">What can be scored</h2>
          <p className="text-sm text-muted-foreground mb-6">
            All {stats.molecules} Suite v4 problems, at the {stats.defaultBasis.replace("cc-pvdz", "cc-pVDZ")} basis.
            Your geometry, charge, spin and active space must match the reference — the exact values
            are printed by{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">qencode.reference(&quot;LiH&quot;)</code>.
          </p>

          <div className="rounded-lg border bg-background overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="text-left font-medium px-4 py-2.5">Molecule</th>
                    <th className="text-left font-medium px-4 py-2.5">Active space</th>
                    <th className="text-left font-medium px-4 py-2.5">Orbitals</th>
                    <th className="text-right font-medium px-4 py-2.5 whitespace-nowrap">Exact E₀ (Ha)</th>
                    <th className="text-right font-medium px-4 py-2.5">Entries</th>
                  </tr>
                </thead>
                <tbody>
                  {molecules.map((m) => (
                    <tr key={`${m.molecule}-${m.orbitalOptimization}`} className="border-t">
                      <td className="px-4 py-2 font-mono text-xs font-medium">{m.molecule}</td>
                      <td className="px-4 py-2 font-mono text-xs text-muted-foreground">
                        [{m.activeElectrons}e, {m.activeOrbitals}o]
                      </td>
                      <td className="px-4 py-2 text-xs text-muted-foreground uppercase">
                        {m.orbitalOptimization}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-xs tabular-nums">
                        {m.exactEnergy.toFixed(6)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono text-xs text-muted-foreground">
                        {m.publishedEntries}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <p className="text-xs text-muted-foreground mt-4">
            Reference energies are exact diagonalisation (CASCI) of the qubit Hamiltonian in the
            declared active space, generated from the {stats.sourceEntries} published entries. The
            same table ships inside the package, and a test fails if the two copies disagree.
            <strong className="text-foreground"> Entries</strong> counts every published entry for
            that problem — certified and research tier alike. N₂ has seven published entries and
            three that meet the threshold; a research-tier entry is a real result that hit the
            method&apos;s limit, not a discarded one.
          </p>

          <p className="text-sm text-muted-foreground mt-5">
            Not on the list? QEncode has no reference for it, so this cannot score it — but{" "}
            <code className="font-mono text-xs bg-muted px-1 rounded">qencode run</code> computes the
            CASCI reference as part of generating an entry. That path does need the chemistry stack.
          </p>
        </div>
      </section>

      {/* ── Next steps ── */}
      <section className="container py-14 max-w-3xl">
        <h2 className="text-xl font-semibold mb-6">If the score looks good</h2>
        <p className="text-sm text-muted-foreground leading-relaxed mb-6">
          The honest next step is to stop self-reporting it. Generate a real entry: the same
          procedure, but with the environment pinned, the provenance recorded, and a content hash
          over the result — which is what makes it something a reviewer can rebuild.
        </p>

        <pre className="bg-muted/50 border rounded-md p-4 text-xs sm:text-sm font-mono overflow-x-auto leading-relaxed mb-6">
{`qencode run --molecule LiH --mapping jordan_wigner --ansatz-type uccsd`}
        </pre>

        <div className="space-y-3 text-sm mb-8">
          {[
            "Runs the fixed pipeline and writes a JSON entry with full provenance",
            "Anyone can re-check it with scripts/verify_entry.py from a clean checkout",
            "Certified and research-tier entries are both published — nothing is discarded for missing a threshold",
          ].map((item) => (
            <div key={item} className="flex items-start gap-2 text-muted-foreground">
              <CheckCircle className="h-4 w-4 mt-0.5 text-green-600 dark:text-green-400 shrink-0" />
              <span>{item}</span>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/leaderboard" data-track="score_leaderboard">
              See the leaderboard <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link href="/leaderboard/guide" data-track="score_guide">What these numbers mean</Link>
          </Button>
          <Button asChild variant="outline">
            <a href={`${REPO}/blob/HEAD/docs/SUBMISSIONS.md`} target="_blank" rel="noopener noreferrer" data-track="score_submissions">
              Submit an entry <ExternalLink className="ml-1 h-3.5 w-3.5" />
            </a>
          </Button>
        </div>
      </section>
    </div>
  );
}
