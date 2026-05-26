import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Zap, ArrowLeft, ExternalLink, FlaskConical } from "lucide-react";

export const dynamic = "force-dynamic";

const GITHUB_RAW = "https://raw.githubusercontent.com/qencode-benchmark/qencode-benchmark/master";

/**
 * Derive the db path from the entry_id filename convention.
 *   *_v4_* or *_ccpvdz_*  → releases/v4/db/    (Suite v4, cc-pVDZ)
 *   *_sto3g_*              → releases/v3/db/    (Suite v3, STO-3G)
 *   *_631g_*               → releases/v3.1/db/  (Suite v3.1, 6-31G)
 */
function dbPath(id) {
  if (id.includes("_v4_") || id.includes("_ccpvdz_")) return "releases/v4/db";
  if (id.includes("_sto3g_") || id.includes("sto-3g"))  return "releases/v3/db";
  if (id.includes("_631g_")  || id.includes("6-31g"))   return "releases/v3.1/db";
  return "releases/v4/db"; // fallback to current suite
}

function isV4(id) {
  return id.includes("_v4_") || id.includes("_ccpvdz_");
}

async function fetchEntry(id) {
  const url = `${GITHUB_RAW}/${dbPath(id)}/${id}.json`;
  try {
    const res = await fetch(url, { next: { revalidate: 3600 } });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function Row({ label, value, mono = false, highlight = false }) {
  return (
    <div className={`flex justify-between items-start py-2 border-b last:border-0 gap-4 ${highlight ? "bg-emerald-50 dark:bg-emerald-950/20 -mx-3 px-3 rounded" : ""}`}>
      <span className="text-xs text-muted-foreground shrink-0 w-44">{label}</span>
      <span className={`text-xs text-right break-all ${mono ? "font-mono" : ""} ${highlight ? "text-emerald-700 dark:text-emerald-400 font-semibold" : ""}`}>
        {value ?? "—"}
      </span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="rounded-lg border p-4 space-y-0.5">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">{title}</h2>
      {children}
    </div>
  );
}

function fmtHa(v) {
  if (v == null) return "—";
  return `${Number(v).toFixed(10)} Ha`;
}

export async function generateMetadata({ params }) {
  const { id } = await params;
  return {
    title: `Entry ${id} | QEncode`,
    description: `Full benchmark artifact and reproducibility details for QEncode entry ${id}`,
    robots: { index: false },
  };
}

export default async function EntryPage({ params }) {
  const { id } = await params;
  const entry = await fetchEntry(id);

  if (!entry) {
    return (
      <div className="container py-16 max-w-2xl">
        <Link href="/leaderboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-8">
          <ArrowLeft className="h-4 w-4" /> Back to leaderboard
        </Link>
        <div className="rounded-lg border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 p-6 text-center">
          <FlaskConical className="h-8 w-8 text-amber-500 mx-auto mb-3" />
          <h1 className="text-lg font-semibold text-amber-900 dark:text-amber-200 mb-2">Entry not yet on GitHub</h1>
          <p className="text-sm text-amber-800 dark:text-amber-300 mb-4">
            Entry <code className="font-mono text-xs bg-amber-100 dark:bg-amber-900 px-1 py-0.5 rounded">{id}</code> exists
            in the production database but has not yet been pushed to the public repository.
            Check back soon — entries are committed after each certification batch.
          </p>
          <Link
            href="/leaderboard"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            ← Back to leaderboard
          </Link>
        </div>
      </div>
    );
  }

  const v4          = isV4(id);
  const prob        = entry.problem ?? {};
  const enc         = entry.encoding ?? {};
  const res         = entry.results ?? {};
  const vqe         = res.vqe ?? {};
  const ref         = res.reference ?? {};
  const cc          = res.classical_comparison ?? {};
  const qual        = res.quality ?? {};
  const prov        = entry.provenance ?? {};
  const tap         = enc.tapering ?? {};
  const cs          = entry.circuit_stats ?? {};
  const active      = prob.active_space ?? {};
  const runCfg      = entry.run_config ?? {};

  const gap           = qual.abs_vqe_exact_gap;
  const beatsClassical = qual.beats_classical;
  const certified     = qual.trusted === true;
  const orbitalOpt    = prob.orbital_optimization ?? active.method ?? null;
  const maxIter       = runCfg.max_iterations ?? runCfg.max_iter ?? null;
  const multistart    = vqe.multistart_runs ?? runCfg.multistart ?? null;
  const backend       = runCfg.backend_type ?? null;

  const githubUrl = `https://github.com/qencode-benchmark/qencode-benchmark/blob/master/${dbPath(id)}/${id}.json`;

  // Build the reproduce command
  const ansatzFlag = enc.ansatz_type?.replace(/_tapered$/, "").replace("hardware_efficient", "hardware_efficient") ?? "";
  const isUccsd    = ansatzFlag.toLowerCase().includes("uccsd");
  const isCasscf   = orbitalOpt === "casscf";
  const repsLine   = (!isUccsd && enc.ansatz_reps != null) ? `  --reps ${enc.ansatz_reps} \\` : null;
  const casscfLine = isCasscf ? `  --orbital-opt casscf \\` : null;
  const maxIterLine = maxIter ? `  --max-iter ${maxIter} \\` : null;
  const multistartLine = multistart ? `  --multistart ${multistart} \\` : null;
  const scriptName = v4 ? "generate_entry_v4.py" : "generate_entry_v3.py";
  const reqFile    = v4 ? "requirements-v4.txt" : "requirements-v3.txt";

  return (
    <div className="container py-12 max-w-3xl">
      {/* Back */}
      <Link href="/leaderboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground mb-6">
        <ArrowLeft className="h-4 w-4" /> Back to leaderboard
      </Link>

      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <h1 className="text-2xl font-bold font-mono">{prob.name}</h1>
          <span className="text-muted-foreground text-sm">/</span>
          <span className="text-sm text-muted-foreground">{enc.mapping?.replace(/_/g, " ")}</span>
          <span className="text-muted-foreground text-sm">/</span>
          <span className="text-sm text-muted-foreground">{enc.ansatz_type?.replace(/_/g, " ")}</span>
        </div>
        <div className="flex flex-wrap gap-2 mb-3">
          {certified ? (
            <Badge className="bg-primary text-primary-foreground gap-1">
              <CheckCircle className="h-3 w-3" /> Certified
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1">Validated (Research)</Badge>
          )}
          {beatsClassical && (
            <Badge className="bg-emerald-600 text-white gap-1" title="VQE gap is smaller than the CCSD(T) correlation energy">
              <Zap className="h-3 w-3" /> Beats CCSD(T)
            </Badge>
          )}
          <Badge variant="outline" className="font-mono text-xs">{prob.basis}</Badge>
          {isCasscf && (
            <Badge className="bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-0 text-xs font-normal">
              CASSCF
            </Badge>
          )}
        </div>
        <p className="text-xs font-mono text-muted-foreground break-all">{entry.entry_id}</p>
      </div>

      {/* Key metrics callout */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "VQE Gap",         value: gap != null ? `${Number(gap).toExponential(4)} Ha` : "—", green: true },
          { label: "CASCI ref",       value: ref.casci_ground_energy_hartree != null ? `${Number(ref.casci_ground_energy_hartree).toFixed(6)} Ha` : "—" },
          { label: "Qubits (tapered)", value: tap.tapered_num_qubits ?? "—" },
          { label: "CCSD(T) corr.",   value: cc.ccsd_t_correlation != null ? `${Number(cc.ccsd_t_correlation).toExponential(3)} Ha` : "—" },
        ].map(({ label, value, green }) => (
          <div key={label} className={`rounded-lg border p-3 ${green ? "border-emerald-200 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950/30" : ""}`}>
            <p className="text-xs text-muted-foreground mb-1">{label}</p>
            <p className={`text-sm font-mono font-semibold ${green ? "text-emerald-700 dark:text-emerald-400" : ""}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        {/* Problem */}
        <Section title="Molecule / Problem">
          <Row label="Name"                value={prob.name} />
          <Row label="Basis set"           value={prob.basis} mono />
          <Row label="Geometry"            value={prob.geometry} mono />
          <Row label="Charge"              value={prob.charge} />
          <Row label="Spin"                value={prob.spin} />
          <Row label="Active electrons"    value={active.num_electrons} />
          <Row label="Active orbitals"     value={active.num_spatial_orbitals} />
          <Row label="Orbital optimization" value={orbitalOpt?.toUpperCase()} />
        </Section>

        {/* Encoding */}
        <Section title="Encoding / Circuit">
          <Row label="Qubit mapping"       value={enc.mapping?.replace(/_/g, "-")} mono />
          <Row label="Ansatz type"         value={enc.ansatz_type} mono />
          {enc.ansatz_reps != null && <Row label="Ansatz reps (HEA)"  value={enc.ansatz_reps} />}
          <Row label="Tapering"            value={tap.enabled ? `Z2 symmetry — ${tap.num_symmetries} symmetries removed` : "None"} />
          <Row label="Qubits (original)"   value={tap.original_num_qubits} />
          <Row label="Qubits (tapered)"    value={tap.tapered_num_qubits} />
          <Row label="Num parameters"      value={cs.ansatz_num_parameters ?? vqe.num_params} />
          {cs.ansatz_depth      != null && <Row label="Circuit depth"   value={cs.ansatz_depth} />}
          {cs.ansatz_num_2q_gates != null && <Row label="2Q gates"      value={cs.ansatz_num_2q_gates} />}
          {isUccsd && (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 px-3 py-2.5 text-xs text-amber-800 dark:text-amber-300 space-y-1">
              <p className="font-semibold">Note on UCCSD circuit metrics</p>
              <p>
                UCCSD uses exponential Pauli operators (<span className="font-mono">exp(iθH)</span>) that are symbolic
                before compilation. Circuit depth and 2-qubit gate counts are not reported here — they depend on the
                target hardware and transpiler.
              </p>
              {(vqe.num_params ?? cs.ansatz_num_parameters) >= 100 && (
                <p>
                  This entry has <strong>{vqe.num_params ?? cs.ansatz_num_parameters} variational parameters</strong> —
                  a large landscape requiring multistart optimisation.
                  {multistart > 0 && ` ${multistart} independent restarts were run.`}
                </p>
              )}
            </div>
          )}
        </Section>

        {/* Energies */}
        <Section title="Energy Results">
          <Row label="HF energy"           value={fmtHa(cc.hf_energy_hartree ?? ref.hf_energy_hartree)} mono />
          <Row label="MP2 energy"          value={fmtHa(cc.mp2_energy_hartree)} mono />
          <Row label="CCSD energy"         value={fmtHa(cc.ccsd_energy_hartree)} mono />
          <Row label="CCSD(T) energy"      value={fmtHa(cc.ccsd_t_energy_hartree)} mono />
          {ref.casscf_energy_hartree != null && (
            <Row label="CASSCF energy"     value={fmtHa(ref.casscf_energy_hartree)} mono />
          )}
          <Row label="CASCI ground state"  value={fmtHa(ref.casci_ground_energy_hartree)} mono />
          <Row label="VQE best energy"     value={fmtHa(vqe.best_energy_hartree)} mono highlight />
          <Row label="|VQE − CASCI| gap"   value={gap != null ? `${Number(gap).toExponential(6)} Ha` : "—"} mono highlight />
          <Row label="CCSD(T) correlation" value={cc.ccsd_t_correlation != null ? `${Number(cc.ccsd_t_correlation).toExponential(6)} Ha` : "—"} mono />
        </Section>

        {/* Optimizer */}
        <Section title="Optimizer / Run Config">
          <Row label="Algorithm"           value={vqe.optimizer ?? runCfg.optimizer} />
          <Row label="Multistart runs"     value={multistart} />
          <Row label="Max iterations"      value={maxIter} />
          <Row label="Total func evals"    value={vqe.nfev?.toLocaleString()} />
          <Row label="Num parameters"      value={vqe.num_params} />
          {backend && <Row label="Backend" value={backend} mono />}
        </Section>

        {/* Provenance */}
        <Section title="Provenance / Reproducibility">
          <Row label="Entry ID"            value={entry.entry_id} mono />
          <Row label="Schema version"      value={entry.schema_version} mono />
          <Row label="Created (UTC)"       value={entry.created_utc} mono />
          <Row label="SHA-256 hash"        value={prov.entry_hash_sha256} mono />
          <Row label="Python"              value={prov.tool_versions?.python} mono />
          <Row label="PySCF"               value={prov.tool_versions?.pyscf} mono />
          <Row label="PennyLane"           value={prov.tool_versions?.pennylane} mono />
          <Row label="OpenFermion"         value={prov.tool_versions?.openfermion} mono />
          <Row label="NumPy"               value={prov.tool_versions?.numpy} mono />
          <Row label="SciPy"               value={prov.tool_versions?.scipy} mono />
        </Section>

        {/* Reproduce */}
        <Section title="Reproduce this result">
          <div className="bg-muted/40 rounded p-3 font-mono text-xs space-y-0.5 mt-1 overflow-x-auto">
            <p className="text-muted-foreground"># Clone repo and install pinned environment</p>
            <p>git clone https://github.com/qencode-benchmark/qencode-benchmark</p>
            <p>cd qencode-benchmark</p>
            <p>pip install -r {reqFile}</p>
            <p className="mt-2 text-muted-foreground"># Run this entry</p>
            <p>python scripts/{scriptName} \</p>
            <p className="pl-4">--molecule {prob.name} \</p>
            <p className="pl-4">--mapping {enc.mapping} \</p>
            <p className="pl-4">--ansatz-type {ansatzFlag} \</p>
            {repsLine   && <p className="pl-4">{repsLine.replace(" \\", " \\")}</p>}
            {casscfLine && <p className="pl-4">--orbital-opt casscf \</p>}
            {multistartLine && <p className="pl-4">--multistart {multistart} \</p>}
            {maxIterLine    && <p className="pl-4">--max-iter {maxIter} \</p>}
            <p className="pl-4">--out-dir releases/{v4 ? "v4" : "v3.1"}/db</p>
          </div>
        </Section>

        {/* GitHub link */}
        <div className="flex justify-end">
          <a
            href={githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground border rounded px-3 py-1.5 hover:bg-muted/50 transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
            View raw JSON on GitHub
          </a>
        </div>
      </div>
    </div>
  );
}
