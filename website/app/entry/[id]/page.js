import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Zap, ArrowLeft, ExternalLink, FlaskConical } from "lucide-react";

export const dynamic = "force-dynamic";

const GITHUB_RAW = "https://raw.githubusercontent.com/qencode-benchmark/qencode-benchmark/master";

/**
 * Derive the db path from the entry_id filename convention.
 *   *_sto3g_*  → releases/v3/db/
 *   *_631g_*   → releases/v3.1/db/
 */
function dbPath(id) {
  if (id.includes("_sto3g_") || id.includes("sto-3g")) return "releases/v3/db";
  if (id.includes("_631g_")  || id.includes("6-31g"))  return "releases/v3.1/db";
  return "releases/v3/db"; // fallback
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

function fmtGap(v) {
  if (v == null || isNaN(v)) return "—";
  const n = Number(v);
  const exp = Math.floor(Math.log10(Math.abs(n)));
  const man = n / Math.pow(10, exp);
  return `${man.toFixed(4)} × 10^${exp} Ha`;
}

export async function generateMetadata({ params }) {
  const { id } = await params;
  return {
    title: `Entry ${id} | QEncode`,
    description: `Full benchmark artifact and reproducibility details for QEncode entry ${id}`,
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
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 text-center">
          <FlaskConical className="h-8 w-8 text-amber-500 mx-auto mb-3" />
          <h1 className="text-lg font-semibold text-amber-900 mb-2">Entry not yet on GitHub</h1>
          <p className="text-sm text-amber-800">
            Entry <code className="font-mono text-xs bg-amber-100 px-1 py-0.5 rounded">{id}</code> exists
            in the production database but has not yet been pushed to the public repository.
            Check back soon — entries are committed after each certification batch.
          </p>
        </div>
      </div>
    );
  }

  const prob  = entry.problem ?? {};
  const enc   = entry.encoding ?? {};
  const res   = entry.results ?? {};
  const vqe   = res.vqe ?? {};
  const ref   = res.reference ?? {};
  const cc    = res.classical_comparison ?? {};
  const qual  = res.quality ?? {};
  const prov  = entry.provenance ?? {};
  const tap   = enc.tapering ?? {};
  const cs    = entry.circuit_stats ?? {};
  const active = prob.active_space ?? {};

  const gap = qual.abs_vqe_exact_gap;
  const beatsClassical = qual.beats_classical;
  const certified = qual.trusted === true;

  const githubUrl = `https://github.com/qencode-benchmark/qencode-benchmark/blob/master/${dbPath(id)}/${id}.json`;

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
            <Badge className="bg-[#185FA5] text-white gap-1">
              <CheckCircle className="h-3 w-3" /> Certified
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1">Validated (Research)</Badge>
          )}
          {beatsClassical && (
            <Badge className="bg-emerald-600 text-white gap-1">
              <Zap className="h-3 w-3" /> Beats Classical
            </Badge>
          )}
          <Badge variant="outline" className="font-mono text-xs">{prob.basis}</Badge>
        </div>
        <p className="text-xs font-mono text-muted-foreground break-all">{entry.entry_id}</p>
      </div>

      {/* Key metrics callout */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        {[
          { label: "VQE Gap", value: gap != null ? `${Number(gap).toExponential(4)} Ha` : "—", green: true },
          { label: "CASCI ref", value: ref.casci_ground_energy_hartree != null ? `${Number(ref.casci_ground_energy_hartree).toFixed(6)} Ha` : "—" },
          { label: "Qubits (tapered)", value: tap.tapered_num_qubits ?? "—" },
          { label: "CCSD(T) corr.", value: cc.ccsd_t_correlation != null ? `${Number(cc.ccsd_t_correlation).toExponential(3)} Ha` : "—" },
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
          <Row label="Name"            value={prob.name} />
          <Row label="Basis set"       value={prob.basis} mono />
          <Row label="Geometry"        value={prob.geometry} mono />
          <Row label="Charge"          value={prob.charge} />
          <Row label="Spin"            value={prob.spin} />
          <Row label="Active electrons" value={active.num_electrons} />
          <Row label="Active orbitals" value={active.num_spatial_orbitals} />
          <Row label="Active space method" value={active.method?.toUpperCase()} />
        </Section>

        {/* Encoding */}
        <Section title="Encoding / Circuit">
          <Row label="Qubit mapping"   value={enc.mapping?.replace(/_/g, "-")} mono />
          <Row label="Ansatz type"     value={enc.ansatz_type} mono />
          <Row label="Ansatz reps"     value={enc.ansatz_reps} />
          <Row label="Tapering"        value={tap.enabled ? `Z2 symmetry — ${tap.num_symmetries} removed` : "None"} />
          <Row label="Qubits (original)" value={tap.original_num_qubits} />
          <Row label="Qubits (tapered)" value={tap.tapered_num_qubits} />
          <Row label="Num parameters"  value={cs.ansatz_num_parameters ?? vqe.num_params} />
          {cs.ansatz_depth   != null && <Row label="Circuit depth"     value={cs.ansatz_depth} />}
          {cs.ansatz_num_2q_gates != null && <Row label="2Q gates"       value={cs.ansatz_num_2q_gates} />}
          {enc.ansatz_type?.toLowerCase().includes("uccsd") && (
            <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950/30 px-3 py-2.5 text-xs text-amber-800 dark:text-amber-300 space-y-1">
              <p className="font-semibold">Note on UCCSD circuit metrics</p>
              <p>
                UCCSD uses exponential Pauli operators (<span className="font-mono">exp(iθH)</span>) that are symbolic
                before compilation. Circuit depth and 2-qubit gate counts are not reported here because they depend
                entirely on the target hardware and transpiler — a 4-qubit UCCSD circuit for LiH expands to
                hundreds of CNOTs after decomposition on a superconducting device.
              </p>
              {(vqe.num_params ?? cs.ansatz_num_parameters) >= 100 && (
                <p>
                  This entry has <strong>{vqe.num_params ?? cs.ansatz_num_parameters} variational parameters</strong> — a
                  large landscape that requires multistart optimisation to reliably find the global minimum.
                  {(vqe.multistart_runs ?? 0) > 0 && ` ${vqe.multistart_runs} independent restarts were run.`}
                </p>
              )}
            </div>
          )}
        </Section>

        {/* Energies */}
        <Section title="Energy Results">
          <Row label="HF energy"         value={fmtHa(cc.hf_energy_hartree ?? ref.hf_energy_hartree)} mono />
          <Row label="MP2 energy"        value={fmtHa(cc.mp2_energy_hartree)} mono />
          <Row label="CCSD energy"       value={fmtHa(cc.ccsd_energy_hartree)} mono />
          <Row label="CCSD(T) energy"    value={fmtHa(cc.ccsd_t_energy_hartree)} mono />
          <Row label="CASCI ground state" value={fmtHa(ref.casci_ground_energy_hartree)} mono />
          <Row label="VQE best energy"   value={fmtHa(vqe.best_energy_hartree)} mono highlight />
          <Row label="|VQE − CASCI| gap" value={gap != null ? `${Number(gap).toExponential(6)} Ha` : "—"} mono highlight />
          <Row label="CCSD(T) correlation" value={cc.ccsd_t_correlation != null ? `${Number(cc.ccsd_t_correlation).toExponential(6)} Ha` : "—"} mono />
        </Section>

        {/* Optimizer */}
        <Section title="Optimizer">
          <Row label="Algorithm"       value={vqe.optimizer} />
          <Row label="Multistart runs" value={vqe.multistart_runs} />
          <Row label="Max iterations"  value="1000" />
          <Row label="Total func evals" value={vqe.nfev?.toLocaleString()} />
          <Row label="Num parameters"  value={vqe.num_params} />
        </Section>

        {/* Provenance */}
        <Section title="Provenance / Reproducibility">
          <Row label="Entry ID"        value={entry.entry_id} mono />
          <Row label="Schema version"  value={entry.schema_version} mono />
          <Row label="Created (UTC)"   value={entry.created_utc} mono />
          <Row label="SHA-256 hash"    value={prov.entry_hash_sha256} mono />
          <Row label="Python"          value={prov.tool_versions?.python} mono />
          <Row label="PySCF"           value={prov.tool_versions?.pyscf} mono />
          <Row label="PennyLane"       value={prov.tool_versions?.pennylane} mono />
          <Row label="OpenFermion"     value={prov.tool_versions?.openfermion} mono />
          <Row label="NumPy"           value={prov.tool_versions?.numpy} mono />
          <Row label="SciPy"           value={prov.tool_versions?.scipy} mono />
        </Section>

        {/* Reproduce */}
        <Section title="Reproduce this result">
          <div className="bg-muted/40 rounded p-3 font-mono text-xs space-y-1 mt-1">
            <p className="text-muted-foreground"># Clone and activate environment</p>
            <p>git clone https://github.com/qencode-benchmark/qencode-benchmark</p>
            <p>cd qencode-benchmark && conda activate qencode</p>
            <p className="mt-2 text-muted-foreground"># Run this specific entry</p>
            <p>python scripts/generate_entry_v3.py \</p>
            <p className="pl-4">--molecule {prob.name} \</p>
            <p className="pl-4">--basis {prob.basis} \</p>
            <p className="pl-4">--mapping {enc.mapping} \</p>
            <p className="pl-4">--ansatz-type {enc.ansatz_type?.replace("_tapered","").replace("uccsd_tapered","uccsd")} \</p>
            <p className="pl-4">--multistart {vqe.multistart_runs ?? 3} \</p>
            <p className="pl-4">--seed 42</p>
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
