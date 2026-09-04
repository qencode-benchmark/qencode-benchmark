"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle, Copy, Check, Crown, Info, TrendingDown, Cpu, BarChart2, Zap, ExternalLink, Sparkles, Target, ShieldCheck, ShieldAlert, AlertTriangle } from "lucide-react";
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import {
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
} from "@/components/ui/tooltip";

// ── Number formatting ──────────────────────────────────────────────────────────

/** Format a gap value nicely: 1.15e-9 → "1.15 × 10⁻⁹" */
function fmtGap(v) {
  if (v == null || isNaN(v)) return "—";
  if (v === 0) return "0";
  const exp = Math.floor(Math.log10(Math.abs(v)));
  const mantissa = v / Math.pow(10, exp);
  const expStr = String(exp)
    .split("")
    .map((c) => {
      const sup = { "0": "⁰","1": "¹","2": "²","3": "³","4": "⁴","5": "⁵","6": "⁶","7": "⁷","8": "⁸","9": "⁹","-": "⁻" };
      return sup[c] ?? c;
    })
    .join("");
  return `${mantissa.toFixed(2)} × 10${expStr}`;
}

/** Compact integer formatter */
function fmtInt(v) {
  if (v == null) return "—";
  return Number(v).toLocaleString();
}

/**
 * How many times more accurate is VQE than CCSD(T)?
 * Returns a string like "70,000×" or null if data missing.
 */
/**
 * Entry IDs on the accuracy-vs-cost Pareto front, computed per molecule.
 *
 * An entry is dominated when another entry for the same molecule is at least as good
 * on both axes -- lower error gap and fewer two-qubit gates -- and strictly better on
 * at least one. What survives is the set of real trade-offs: every non-dominated entry
 * is the most accurate available at its cost, and every dominated entry is beaten
 * outright by something else in the suite.
 *
 * Grouped per molecule on purpose. Gaps are not comparable across molecules -- H2
 * converges to 1e-16 and H10 to 1e-2 -- so a single global front would simply rank the
 * easy systems first and say nothing about method choice.
 */
function paretoOptimalIds(rows) {
  const byMolecule = new Map();
  rows.forEach((r) => {
    if (r.gap == null || r.twoQ == null || !r.entryId) return;
    if (!byMolecule.has(r.molecule)) byMolecule.set(r.molecule, []);
    byMolecule.get(r.molecule).push(r);
  });
  const ids = new Set();
  byMolecule.forEach((group) => {
    group.forEach((a) => {
      const dominated = group.some(
        (b) =>
          b !== a &&
          b.gap <= a.gap &&
          b.twoQ <= a.twoQ &&
          (b.gap < a.gap || b.twoQ < a.twoQ)
      );
      if (!dominated) ids.add(a.entryId);
    });
  });
  return ids;
}

function fmtClassicalRatio(gap, ccsdTCorrelation) {
  if (gap == null || ccsdTCorrelation == null || gap <= 0 || ccsdTCorrelation <= 0) return null;
  const absCorr = Math.abs(ccsdTCorrelation);
  const ratio   = absCorr / gap;
  if (ratio >= 1000) return `${Math.round(ratio / 1000).toLocaleString()}k×`;
  if (ratio >= 10)   return `${Math.round(ratio).toLocaleString()}×`;
  return `${ratio.toFixed(1)}×`;
}

/** Display label for mapping key */
function mappingLabel(m) {
  const map = {
    jordan_wigner: "Jordan-Wigner",
    parity: "Parity",
    bravyi_kitaev: "Bravyi-Kitaev",
    bravyi_kitaev_tree: "BK Tree",
  };
  return map[m] ?? m;
}

/** Display label for ansatz key */
function ansatzLabel(a) {
  const map = {
    UCCSD: "UCCSD",
    hardware_efficient: "HEA",
    adapt_vqe: "ADAPT-VQE",
    kUpCCGSD: "k-UpCCGSD",
  };
  return map[a] ?? a;
}

// ── Small helper components ────────────────────────────────────────────────────

function CopyConfig({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="inline-flex items-center gap-1.5 font-mono text-xs hover:text-primary transition-colors group"
      title="Copy config string"
    >
      {text}
      {copied
        ? <Check className="h-3 w-3 text-green-500 shrink-0" />
        : <Copy className="h-3 w-3 opacity-0 group-hover:opacity-50 transition-opacity shrink-0" />}
    </button>
  );
}

function GapBar({ value, minValue, maxValue }) {
  if (value == null || maxValue == null || maxValue === 0) return null;

  const logVal = Math.log10(Math.max(value, 1e-30));
  const logMax = Math.log10(Math.max(maxValue, 1e-30));
  // Scale from actual min to actual max of the visible set so every filtered
  // view shows green (best) → red (worst) within its own range.
  // Fall back to a 6-decade window when there is only one entry.
  const logMin = (minValue != null && minValue < maxValue)
    ? Math.log10(Math.max(minValue, 1e-30))
    : logMax - 6;
  const range = Math.max(logMax - logMin, 0.01);
  const pct = Math.max(0, Math.min(100, ((logVal - logMin) / range) * 100));

  // Color: green for low (good), amber for mid, red for high
  const color = pct < 20 ? "bg-green-500" : pct < 55 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden shrink-0">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function FilterChip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`
        px-2.5 py-1 rounded-full text-xs font-medium border transition-colors
        ${active
          ? "bg-primary text-white border-primary"
          : "bg-background text-muted-foreground border-border hover:border-primary hover:text-foreground"}
      `}
    >
      {label}
    </button>
  );
}

// ── Main table renderer ────────────────────────────────────────────────────────

// ── Certification margin and fragility ────────────────────────────────────────
//
// Two entries certified at 9.98 mHa and 0.001 mHa are both "certified", and the table
// used to show them identically. Only one survives being re-run on another machine.
// margin = 0.01 Ha − gap, shown as a share of the threshold. The risk is the conjunction
// of a thin margin and an amplifying configuration (gradient-free optimiser on an
// unstructured ansatz), and it is a prediction until an entry has actually been re-run.

const CERT_THRESHOLD = 0.01;
const THIN_FRACTION  = 0.2;

function Tip({ children, content }) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs space-y-1">{content}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function MarginCell({ r }) {
  if (r.margin == null || r.margin <= 0) {
    return <span className="text-xs text-muted-foreground/60">—</span>;
  }
  const frac = r.margin / CERT_THRESHOLD;
  const thin = frac < THIN_FRACTION;
  const pct  = frac >= 0.1 ? `${Math.round(frac * 100)}%` : `${(frac * 100).toFixed(1)}%`;
  const tone = thin
    ? (r.amplifies && !r.robustness ? "text-amber-700 dark:text-amber-400" : "text-muted-foreground")
    : "text-foreground";
  return (
    <Tip content={
      <>
        <p className="font-semibold">Certification margin</p>
        <p>0.01 Ha − gap = <span className="font-mono">{fmtGap(r.margin)} Ha</span> — {pct} of the threshold.</p>
        <p className="text-muted-foreground">
          How far the energy can move before this entry stops certifying. Margin bounds how
          far it <em>can</em> move, not how far it <em>will</em>: that depends on the optimiser
          and ansatz.
        </p>
        {thin && (
          <p className="text-amber-300 font-medium">
            Thin margin (under {THIN_FRACTION * 100}% of the threshold).
          </p>
        )}
      </>
    }>
      <span className={`inline-flex items-center gap-1 font-mono text-xs tabular-nums cursor-help ${tone}`}>
        {pct}
        {thin && r.amplifies && !r.robustness && <AlertTriangle className="h-3 w-3 shrink-0" />}
      </span>
    </Tip>
  );
}

function OptimizerChip({ r }) {
  if (!r.optimizer) return null;
  const free = r.optimiserFamily === "gradient-free";
  const tone = r.amplifies
    ? "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
    : "border-border bg-muted/40 text-muted-foreground";
  return (
    <Tip content={
      <>
        <p className="font-semibold">Optimiser: {r.optimizer}</p>
        <p className="text-muted-foreground">
          {free ? "Gradient-free." : "Gradient-based."}{" "}
          {r.amplifies
            ? "A gradient-free optimiser on an unstructured ansatz amplifies last-bit arithmetic differences into a different local minimum, so the energy can move by up to ~10⁻² Ha on another machine while still certifying. Measured: HEA/COBYLA entries moved 10³–10⁴× more across environments than ADAPT entries."
            : r.optimiserFamily === "gradient-free"
              ? "ADAPT-VQE selects its operators by analytic gradient, so the ansatz structure is gradient-determined and the inner optimiser only polishes a small, well-conditioned set. Measured to move ≤10⁻⁶ Ha across environments."
              : "Effectively immune to the comparison-flipping that makes gradient-free runs environment-sensitive. Measured to move ≤10⁻⁶ Ha across environments."}
        </p>
      </>
    }>
      <span className={`inline-flex items-center rounded border px-1 py-0 text-[10px] font-mono leading-4 cursor-help ${tone}`}>
        {r.optimizer}
      </span>
    </Tip>
  );
}

function FragilityBadges({ r }) {
  const out = [];
  if (r.chemAccurate) {
    out.push(
      <Tip key="chem" content={
        <>
          <p className="font-semibold">Chemical accuracy</p>
          <p className="text-muted-foreground">Gap below 1.6 × 10⁻³ Ha (1 kcal/mol) — accurate enough to make a chemical prediction with. Reported, not a certification criterion; 26 of 54 entries reach it.</p>
        </>
      }>
        <Badge variant="outline" className="text-xs gap-1 cursor-help border-sky-400 text-sky-700 dark:text-sky-300">
          <Target className="h-3 w-3 shrink-0" /> Chem. accuracy
        </Badge>
      </Tip>
    );
  }
  if (r.robustness === "robust") {
    out.push(
      <Tip key="rob" content={
        <>
          <p className="font-semibold">Re-run on another environment: still certifies</p>
          <p className="text-muted-foreground">Regenerated on a machine with drifted package versions and the energy moved far less than its own margin. Measured, not inferred.</p>
        </>
      }>
        <Badge variant="outline" className="text-xs gap-1 cursor-help border-emerald-500 text-emerald-700 dark:text-emerald-300">
          <ShieldCheck className="h-3 w-3 shrink-0" /> Re-run: robust
        </Badge>
      </Tip>
    );
  } else if (r.robustness === "marginal") {
    out.push(
      <Tip key="marg" content={
        <>
          <p className="font-semibold">Re-run on another environment: passed on the sign</p>
          <p className="text-muted-foreground">It still certifies, but the energy moved <em>further than its own margin</em> and survived only because the movement happened to be toward the reference. The opposite sign would have failed it. Not evidence of stability.</p>
        </>
      }>
        <Badge variant="outline" className="text-xs gap-1 cursor-help border-amber-500 text-amber-700 dark:text-amber-300">
          <ShieldAlert className="h-3 w-3 shrink-0" /> Re-run: marginal
        </Badge>
      </Tip>
    );
  } else if (r.robustness === "fragile") {
    out.push(
      <Tip key="frag" content={
        <>
          <p className="font-semibold">Re-run on another environment: does not certify</p>
          <p className="text-muted-foreground">Reproduces exactly on the reference pinned environment, which is what certification attests, but regenerates above 0.01 Ha on a machine with drifted package versions. Flagged, not withdrawn.</p>
        </>
      }>
        <Badge variant="outline" className="text-xs gap-1 cursor-help border-red-500 text-red-700 dark:text-red-300">
          <ShieldAlert className="h-3 w-3 shrink-0" /> Re-run: fragile
        </Badge>
      </Tip>
    );
  } else if (r.atRisk) {
    out.push(
      <Tip key="risk" content={
        <>
          <p className="font-semibold">Predicted fragile, not yet re-run</p>
          <p className="text-muted-foreground">Thin margin <em>and</em> an amplifying configuration — the combination measured to fail re-certification elsewhere. A prediction until this entry is actually regenerated on another environment.</p>
        </>
      }>
        <Badge variant="outline" className="text-xs gap-1 cursor-help border-amber-400 text-amber-700 dark:text-amber-300">
          <AlertTriangle className="h-3 w-3 shrink-0" /> At risk
        </Badge>
      </Tip>
    );
  }
  return out;
}

function LeaderboardTable({ rows, category, basisLabel, paretoIds = null }) {
  const includeBalanced  = category === "balanced";
  const includeHardware  = category === "cost" || category === "balanced";
  // The balanced view is the only place accuracy and cost are meant to be read together,
  // so it carries the classical baseline alongside the hardware columns. Without it a
  // visitor never sees "how close to CCSD(T)" and "what it costs" on the same row.
  const includeClassical = category === "accuracy" || category === "research"
                        || category === "balanced";

  // Gap range in this filtered set (for bar scale)
  const gapVals = useMemo(() => rows.map((r) => r.gap).filter((v) => v != null && v > 0), [rows]);
  const minGap  = useMemo(() => gapVals.length ? Math.min(...gapVals) : null, [gapVals]);
  const maxGap  = useMemo(() => gapVals.length ? Math.max(...gapVals) : null, [gapVals]);

  if (rows.length === 0) {
    return (
      <div className="rounded-lg border bg-muted/20 py-12 text-center text-sm text-muted-foreground">
        No entries match the current filters.
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-12 text-center">Rank</TableHead>
            <TableHead>Molecule</TableHead>
            <TableHead>Mapping</TableHead>
            <TableHead>Ansatz</TableHead>
            <TableHead className="text-right">
              <span className="flex items-center justify-end gap-1">
                Error Gap
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3 w-3 text-muted-foreground cursor-help shrink-0" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs text-xs">
                      |E_VQE − E_CASCI| in Hartrees. Chemical accuracy = 1.6 × 10⁻³ Ha.
                      CASCI is the full-CI reference within the active space — the exact result
                      the VQE is trying to reach. Lower is better.{basisLabel ? ` Computed with ${basisLabel} basis set.` : ""}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </span>
            </TableHead>
            <TableHead className="w-20"></TableHead>
            <TableHead className="text-right">
              <span className="flex items-center justify-end gap-1">
                Margin
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3 w-3 text-muted-foreground cursor-help shrink-0" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs text-xs space-y-1">
                      <p className="font-semibold">Certification margin</p>
                      <p>0.01 Ha − gap, as a share of the 0.01 Ha threshold. How much room the
                        entry has before a re-run on another machine could push it over the line.</p>
                      <p className="text-muted-foreground">Under 20% is thin. Whether thin is
                        dangerous depends on the optimiser chip: a gradient-free optimiser on an
                        unstructured ansatz can move ~10⁻² Ha across environments; ADAPT and
                        gradient-based runs move ~10⁻⁶ Ha.</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </span>
            </TableHead>
            {includeClassical && (
              <TableHead className="text-right">
                <span className="flex items-center justify-end gap-1">
                  CCSD(T) corr.
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info className="h-3 w-3 text-muted-foreground cursor-help shrink-0" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs text-xs">
                        |CCSD(T) correlation energy| — the best classical perturbative result
                        for this molecule. VQE entries with a smaller gap beat this classical baseline.
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </span>
              </TableHead>
            )}
            {includeHardware && (
              <>
                <TableHead className="text-right">2Q Gates</TableHead>
                <TableHead className="text-right">Depth</TableHead>
                <TableHead className="text-right">
                  <span className="flex items-center justify-end gap-1">
                    T gates
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="h-3 w-3 text-muted-foreground cursor-help shrink-0" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs text-xs">
                          <p className="font-semibold">Fault-tolerant resource estimate</p>
                          <p className="text-muted-foreground">
                            Estimated T-gate count for this ansatz, from the non-Clifford
                            rotations in the pre-transpilation circuit. T gates dominate the
                            cost of a fault-tolerant implementation, so this is the
                            resource-relevant figure — not the 2-qubit gate count.
                          </p>
                          <p className="text-muted-foreground">
                            An estimate, not a compiled count: it assumes standard rotation
                            synthesis and no hardware routing.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </span>
                </TableHead>
              </>
            )}
            {includeBalanced && (
              <TableHead className="text-right">Score</TableHead>
            )}
            <TableHead className="text-right w-24">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, idx) => {
            const isFirst = r.rank === 1;
            const configStr = `${r.molecule.toLowerCase()}-${r.mapping}-${r.ansatz}-v4`;
            return (
              <TableRow
                key={`${r.molecule}-${r.mapping}-${r.ansatz}-${idx}`}
                className={`hover:bg-muted/30 transition-colors ${isFirst ? "bg-amber-50/40 dark:bg-amber-950/10" : ""}`}
              >
                {/* Rank */}
                <TableCell className="text-center">
                  {isFirst ? (
                    <span className="inline-flex items-center justify-center">
                      <Crown className="h-4 w-4 text-amber-500 shrink-0" />
                    </span>
                  ) : (
                    <span className="font-mono text-sm text-muted-foreground">#{r.rank}</span>
                  )}
                </TableCell>

                {/* Molecule */}
                <TableCell>
                  <div className="flex flex-col gap-0.5">
                    <span className="font-mono text-sm font-medium">{r.molecule}</span>
                    <div className="flex items-center gap-1 flex-wrap">
                      {r.basis && (
                        <span className="text-[10px] font-mono px-1 py-0 rounded border border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300 leading-4">
                          {r.basis}
                        </span>
                      )}
                      {r.orbitalOpt === "casscf" && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="text-[10px] font-mono px-1 py-0 rounded border border-purple-200 bg-purple-50 text-purple-700 dark:border-purple-800 dark:bg-purple-950 dark:text-purple-300 leading-4 cursor-help">
                                CASSCF
                              </span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs text-xs">
                              Orbitals pre-optimised with CASSCF before VQE. Required for molecules
                              with strong multireference character (e.g. N2 triple bond).
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </div>
                  </div>
                </TableCell>

                {/* Mapping */}
                <TableCell>
                  <span className="text-xs text-muted-foreground">
                    {mappingLabel(r.mapping)}
                  </span>
                </TableCell>

                {/* Ansatz */}
                <TableCell>
                  <div className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-muted-foreground">{ansatzLabel(r.ansatz)}</span>
                      <CopyConfig text={configStr} />
                    </div>
                    <OptimizerChip r={r} />
                  </div>
                </TableCell>

                {/* Gap value */}
                <TableCell className="text-right font-mono text-xs tabular-nums">
                  {fmtGap(r.gap)}
                </TableCell>

                {/* Gap bar */}
                <TableCell>
                  <GapBar value={r.gap} minValue={minGap} maxValue={maxGap} />
                </TableCell>

                {/* Certification margin */}
                <TableCell className="text-right">
                  <MarginCell r={r} />
                </TableCell>

                {/* CCSD(T) correlation — classical baseline */}
                {includeClassical && (
                  <TableCell className="text-right font-mono text-xs tabular-nums text-muted-foreground">
                    {fmtGap(r.ccsdTCorrelation != null ? Math.abs(r.ccsdTCorrelation) : null)}
                  </TableCell>
                )}

                {/* Hardware columns */}
                {includeHardware && (
                  <>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {fmtInt(r.twoQ)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {fmtInt(r.depth)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums text-muted-foreground">
                      {fmtInt(r.tGateEstimate)}
                    </TableCell>
                  </>
                )}

                {/* Balanced score */}
                {includeBalanced && (
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {r.balancedScore?.toFixed ? r.balancedScore.toFixed(4) : "—"}
                  </TableCell>
                )}

                {/* Status */}
                <TableCell className="text-right">
                  <div className="flex flex-col items-end gap-1">
                    {r.entryId && (
                      <Link
                        href={`/entry/${r.entryId}`}
                        className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline transition-colors"
                        title="View full benchmark artifact"
                      >
                        <ExternalLink className="h-3 w-3 shrink-0" /> View entry
                      </Link>
                    )}
                    {r.baseline ? (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge className="bg-primary text-white text-xs gap-1 cursor-help">
                              <CheckCircle className="h-3 w-3 shrink-0" /> Baseline
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs text-xs">
                            Baseline entries are run by the QEncode team using standard reference
                            implementations. They establish the floor for each configuration.
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    ) : (
                      <Badge variant="secondary" className="text-xs gap-1">
                        <CheckCircle className="h-3 w-3 text-green-500 shrink-0" /> Verified
                      </Badge>
                    )}
                    {paretoIds && paretoIds.has(r.entryId) && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge variant="outline" className="text-xs gap-1 cursor-help border-violet-400 text-violet-700 dark:text-violet-300">
                              <Sparkles className="h-3 w-3 shrink-0" /> Pareto
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs text-xs space-y-1">
                            <p className="font-semibold">On the accuracy-vs-cost frontier</p>
                            <p className="text-muted-foreground">
                              No other entry for this molecule is both at least as accurate and
                              at least as cheap. It is the most accurate option available at its
                              two-qubit gate count, so it is a genuine trade-off rather than a
                              choice something else beats outright.
                            </p>
                            <p className="text-muted-foreground">
                              Computed per molecule: gaps are not comparable between molecules.
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                    <FragilityBadges r={r} />
                    {r.beatsClassical && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Badge className="bg-emerald-600 text-white text-xs gap-1 cursor-help">
                              <Zap className="h-3 w-3 shrink-0" /> Beats CCSD(T)
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs text-xs space-y-1">
                            <p className="font-semibold">VQE error gap &lt; CCSD(T) correlation energy</p>
                            <p className="text-muted-foreground">This means the VQE simulation error is smaller than the best single-reference perturbative classical result — not that quantum beats classical computing overall.</p>
                            <p>VQE gap: <span className="font-mono">{fmtGap(r.gap)} Ha</span></p>
                            {r.ccsdTCorrelation != null && (
                              <p>CCSD(T) corr.: <span className="font-mono">{fmtGap(Math.abs(r.ccsdTCorrelation))} Ha</span></p>
                            )}
                            {fmtClassicalRatio(r.gap, r.ccsdTCorrelation) && (
                              <p className="text-emerald-300 font-medium">
                                VQE is {fmtClassicalRatio(r.gap, r.ccsdTCorrelation)} more accurate than CCSD(T)
                              </p>
                            )}
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

// ── Main export ────────────────────────────────────────────────────────────────

export default function LeaderboardClient({ acc, cost, balanced, research = [], basisLabel = null }) {
  const all = useMemo(() => [...acc, ...cost, ...balanced], [acc, cost, balanced]);

  // Collect unique filter options
  const molecules = useMemo(
    () => ["All", ...Array.from(new Set(all.map((r) => r.molecule))).sort()],
    [all]
  );
  const mappings = useMemo(
    () => Array.from(new Set(all.map((r) => r.mapping).filter(Boolean))).sort(),
    [all]
  );
  const ansatze = useMemo(
    () => Array.from(new Set(all.map((r) => r.ansatz).filter(Boolean))).sort(),
    [all]
  );

  // Filter state
  const [molecule, setMolecule] = useState("All");
  const [activeMappings, setActiveMappings] = useState(new Set(mappings));
  const [activeAnsatze, setActiveAnsatze] = useState(new Set(ansatze));

  // Keep filter sets in sync if new mappings/ansatze appear
  useMemo(() => {
    setActiveMappings((prev) => {
      const next = new Set(prev);
      mappings.forEach((m) => { if (!next.has(m)) next.add(m); });
      return next;
    });
  }, [mappings]);

  useMemo(() => {
    setActiveAnsatze((prev) => {
      const next = new Set(prev);
      ansatze.forEach((a) => { if (!next.has(a)) next.add(a); });
      return next;
    });
  }, [ansatze]);

  function toggleMapping(m) {
    setActiveMappings((prev) => {
      const next = new Set(prev);
      if (next.has(m)) { next.delete(m); } else { next.add(m); }
      return next;
    });
  }

  function toggleAnsatz(a) {
    setActiveAnsatze((prev) => {
      const next = new Set(prev);
      if (next.has(a)) { next.delete(a); } else { next.add(a); }
      return next;
    });
  }

  function applyFilters(rows) {
    return rows.filter((r) =>
      (molecule === "All" || r.molecule === molecule) &&
      activeMappings.has(r.mapping) &&
      activeAnsatze.has(r.ansatz)
    );
  }

  // The frontier is a property of the full certified set, not of the current view:
  // hiding an ansatz with a filter does not make a dominated entry undominated.
  const paretoIds = useMemo(() => paretoOptimalIds(cost), [cost]);
  const [paretoOnly, setParetoOnly] = useState(false);

  const filteredAcc      = useMemo(() => applyFilters(acc), [acc, molecule, activeMappings, activeAnsatze]);
  const filteredCost     = useMemo(() => applyFilters(cost).filter((r) => r.twoQ != null && r.depth != null).filter((r) => !paretoOnly || paretoIds.has(r.entryId)), [cost, molecule, activeMappings, activeAnsatze, paretoOnly, paretoIds]);
  const filteredBalanced = useMemo(() => applyFilters(balanced).filter((r) => r.twoQ != null && r.depth != null).filter((r) => !paretoOnly || paretoIds.has(r.entryId)), [balanced, molecule, activeMappings, activeAnsatze, paretoOnly, paretoIds]);
  const filteredResearch = useMemo(() => applyFilters(research), [research, molecule, activeMappings, activeAnsatze]);

  // Use accuracy tab length as the canonical "certified entry" count — cost and balanced
  // are subsets of the same entries, so summing all three would triple-count them.
  const totalVisible = filteredAcc.length;

  // Controlled tab state — fall back to "accuracy" if Research tab disappears due to filter change
  const [activeTab, setActiveTab] = useState("accuracy");
  useMemo(() => {
    if (activeTab === "research" && filteredResearch.length === 0) {
      setActiveTab("accuracy");
    }
  }, [filteredResearch.length]);

  return (
    <div className="space-y-6">
      {/* ── Filter bar ─────────────────────────────────────────────────────── */}
      <div className="rounded-lg border bg-muted/20 p-4 space-y-4">
        {/* Molecule selector */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-20 shrink-0">
            Molecule
          </span>
          <div className="flex flex-wrap gap-1.5">
            {molecules.map((m) => (
              <FilterChip
                key={m}
                label={m === "All" ? "All molecules" : m}
                active={molecule === m}
                onClick={() => setMolecule(m)}
              />
            ))}
          </div>
        </div>

        {/* Mapping filter */}
        {mappings.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-20 shrink-0">
              Mapping
            </span>
            <div className="flex flex-wrap gap-1.5">
              {mappings.map((m) => (
                <FilterChip
                  key={m}
                  label={mappingLabel(m)}
                  active={activeMappings.has(m)}
                  onClick={() => toggleMapping(m)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Ansatz filter */}
        {ansatze.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-20 shrink-0">
              Ansatz
            </span>
            <div className="flex flex-wrap gap-1.5">
              {ansatze.map((a) => (
                <FilterChip
                  key={a}
                  label={ansatzLabel(a)}
                  active={activeAnsatze.has(a)}
                  onClick={() => toggleAnsatz(a)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Frontier filter — applies to the two cost-aware boards */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide w-20 shrink-0">
            Frontier
          </span>
          <div className="flex flex-wrap items-center gap-2">
            <FilterChip
              label="Pareto-optimal only"
              active={paretoOnly}
              onClick={() => setParetoOnly((v) => !v)}
            />
            <span className="text-xs text-muted-foreground">
              non-dominated on accuracy vs 2Q gates, per molecule — affects Lowest Cost and Balanced
            </span>
          </div>
        </div>

        {/* Active count */}
        <div className="flex items-center justify-between pt-1 border-t">
          <p className="text-xs text-muted-foreground">
            {totalVisible} certified {totalVisible === 1 ? "entry" : "entries"} match{totalVisible === 1 ? "es" : ""} current filters
          </p>
          <button
            onClick={() => {
              setMolecule("All");
              setActiveMappings(new Set(mappings));
              setActiveAnsatze(new Set(ansatze));
              setParetoOnly(false);
            }}
            className="text-xs text-muted-foreground underline hover:text-foreground transition-colors"
          >
            Reset filters
          </button>
        </div>
      </div>

      {/* ── Category tabs ──────────────────────────────────────────────────── */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="w-full sm:w-auto h-auto flex-wrap gap-1">
          <TabsTrigger value="accuracy" className="flex items-center gap-1.5">
            <TrendingDown className="h-3.5 w-3.5 shrink-0" />
            Best Accuracy
            <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-mono">
              {filteredAcc.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="cost" className="flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5 shrink-0" />
            Lowest Cost
            <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-mono">
              {filteredCost.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="balanced" className="flex items-center gap-1.5">
            <BarChart2 className="h-3.5 w-3.5 shrink-0" />
            Balanced
            <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-mono">
              {filteredBalanced.length}
            </span>
          </TabsTrigger>
          {filteredResearch.length > 0 && (
            <TabsTrigger value="research" className="flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 shrink-0" />
              Research
              <span className="ml-1 rounded-full bg-amber-100 text-amber-800 px-1.5 py-0.5 text-xs font-mono">
                {filteredResearch.length}
              </span>
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="accuracy" className="mt-6">
          <div className="mb-3">
            <h3 className="text-sm font-medium text-foreground">Best Accuracy</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ranked by lowest |E<sub>VQE</sub> − E<sub>CASCI</sub>| error gap. Chemical accuracy threshold: 1.6 × 10⁻³ Ha.
            </p>
          </div>
          <LeaderboardTable rows={filteredAcc} category="accuracy" basisLabel={basisLabel} />
        </TabsContent>

        <TabsContent value="cost" className="mt-6">
          <div className="mb-3">
            <h3 className="text-sm font-medium text-foreground">Lowest Hardware Cost</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ranked by fewest two-qubit gates (then circuit depth). Entries without transpiled metrics are excluded.
            </p>
          </div>
          <LeaderboardTable rows={filteredCost} category="cost" basisLabel={basisLabel} paretoIds={paretoIds} />
        </TabsContent>

        <TabsContent value="balanced" className="mt-6">
          <div className="mb-3">
            <h3 className="text-sm font-medium text-foreground">Balanced Score</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Combined score weighting accuracy and hardware cost equally. Lower is better.
            </p>
          </div>
          <LeaderboardTable rows={filteredBalanced} category="balanced" basisLabel={basisLabel} paretoIds={paretoIds} />
        </TabsContent>

        {filteredResearch.length > 0 && (
          <TabsContent value="research" className="mt-6">
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
              <h3 className="text-sm font-semibold text-amber-900 flex items-center gap-1.5">
                <Info className="h-4 w-4 shrink-0" />
                Advanced Benchmark — Research Tier
              </h3>
              <p className="text-xs text-amber-800 mt-1">
                These entries are <strong>validated</strong> but do not meet the 0.01 Ha certification threshold.
                They represent strongly-correlated systems or mapping configurations where
                standard UCCSD reaches its physical limit{basisLabel ? ` with the ${basisLabel} basis` : ""}. Results are reproducible and correct —
                the gap reflects the method&apos;s limitation, not an implementation error.
                Entries that do meet the CCSD(T) threshold carry the <strong>Beats CCSD(T)</strong> badge,
                which means the VQE error is smaller than the best single-reference perturbative classical result
                for that molecule — not that quantum beats classical computing overall.
              </p>
            </div>
            <LeaderboardTable rows={filteredResearch} category="research" basisLabel={basisLabel} />
          </TabsContent>
        )}
      </Tabs>

      {/* ── Legend ─────────────────────────────────────────────────────────── */}
      <div className="rounded-lg border bg-muted/10 p-4">
        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">Legend</p>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Crown className="h-3.5 w-3.5 text-amber-500 shrink-0" /> Rank #1 in category
          </span>
          <span className="flex items-center gap-1.5">
            <Badge className="bg-primary text-white text-xs">Baseline</Badge>
            Run by QEncode team
          </span>
          <span className="flex items-center gap-1.5">
            <Badge variant="secondary" className="text-xs">Verified</Badge>
            Community submission
          </span>
          <span className="flex items-center gap-1.5">
            <Badge className="bg-emerald-600 text-white text-xs gap-1">
              <Zap className="h-3 w-3 shrink-0" /> Beats CCSD(T)
            </Badge>
            VQE error &lt; CCSD(T) correlation energy — hover for details
          </span>
          <span className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-xs gap-1 border-sky-400 text-sky-700 dark:text-sky-300">
              <Target className="h-3 w-3 shrink-0" /> Chem. accuracy
            </Badge>
            Gap &lt; 1.6 × 10⁻³ Ha — reported, not a criterion
          </span>
          <span className="flex items-center gap-1.5">
            <span className="font-mono text-xs">Margin</span>
            0.01 Ha − gap, as a share of the threshold; under 20% is thin
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-flex items-center rounded border border-amber-300 bg-amber-50 text-amber-800 px-1 text-[10px] font-mono leading-4">COBYLA</span>
            Amber optimiser chip = amplifying configuration (gradient-free on an unstructured ansatz)
          </span>
          <span className="flex items-center gap-1.5">
            <Badge variant="outline" className="text-xs gap-1 border-emerald-500 text-emerald-700 dark:text-emerald-300">
              <ShieldCheck className="h-3 w-3 shrink-0" /> Re-run
            </Badge>
            Measured on another environment: robust / marginal / fragile — hover for details
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-10 h-1.5 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-1/4 bg-green-500 rounded-full" />
            </div>
            Relative gap (log scale, green = best)
          </span>
        </div>
      </div>

      {/* ── Ansatz guide ───────────────────────────────────────────────────── */}
      <details className="group rounded-lg border bg-muted/10 text-xs">
        <summary className="flex cursor-pointer select-none items-center gap-2 p-4 font-medium text-muted-foreground hover:text-foreground transition-colors list-none">
          <Info className="h-3.5 w-3.5 shrink-0" />
          Ansatz guide — UCCSD vs HEA vs ADAPT-VQE, and why some circuit metrics show &ldquo;—&rdquo;
          <span className="ml-auto text-muted-foreground/50 group-open:rotate-180 transition-transform">▾</span>
        </summary>
        <div className="border-t px-4 pb-4 pt-3 space-y-4 text-muted-foreground">
          <div className="grid gap-3 sm:grid-cols-2">
            {/* UCCSD */}
            <div className="rounded-md border bg-background p-3 space-y-1.5">
              <p className="font-semibold text-foreground">UCCSD — Unitary Coupled Cluster</p>
              <p>Chemistry-motivated ansatz that applies all single and double electronic excitations from the Hartree-Fock reference state. Produces the best energies because the circuit is designed around the molecule&apos;s physics.</p>
              <p className="text-amber-700 dark:text-amber-400 font-medium">Why 2Q gates and depth show &ldquo;—&rdquo;:</p>
              <p>UCCSD uses exponential Pauli operators (<span className="font-mono">exp(iθH)</span>) that are symbolic until compiled for a specific hardware target. The raw gate count before transpilation is not meaningful for hardware comparison, so these columns are intentionally left blank. On real superconducting hardware, a single UCCSD layer for LiH (4 qubits) typically expands to hundreds of CNOT gates after decomposition.</p>
              <p className="text-emerald-700 dark:text-emerald-400 font-medium">N₂ — certified at cc-pVDZ:</p>
              <p>N₂ with cc-pVDZ has 404 UCCSD parameters and a strongly-correlated triple bond. With CASSCF orbital optimisation, QEncode certified N₂ JW/UCCSD at 2.015 mHa gap — within chemical accuracy and aligned with DARPA QB-GSEE targets. Without CASSCF (HEA), the gap exceeds 0.1 Ha, illustrating how critical orbital optimisation is for multireference systems.</p>
            </div>
            {/* HEA */}
            <div className="rounded-md border bg-background p-3 space-y-1.5">
              <p className="font-semibold text-foreground">HEA — Hardware-Efficient Ansatz</p>
              <p>Brick-layer circuit of alternating single-qubit rotations (RY) and CNOT entanglers, repeated for a fixed number of layers. The structure is chosen to minimise gate count on near-term devices rather than to match any chemical property of the molecule.</p>
              <p className="text-emerald-700 dark:text-emerald-400 font-medium">Why 2Q gates and depth are shown:</p>
              <p>HEA uses only native hardware gates (RY, CNOT), so the circuit is already in a hardware-ready form. Gate counts reflect what would actually run on a device — making HEA entries directly comparable in the Lowest Cost and Balanced categories.</p>
              <p className="text-emerald-700 dark:text-emerald-400 font-medium">Trade-off:</p>
              <p>HEA achieves near-chemical-accuracy for small molecules but may plateau before reaching UCCSD accuracy on larger or strongly-correlated systems, since it has no built-in knowledge of the molecular Hamiltonian.</p>
            </div>
            {/* ADAPT-VQE */}
            <div className="rounded-md border bg-background p-3 space-y-1.5">
              <p className="font-semibold text-foreground">ADAPT-VQE — Adaptive Ansatz</p>
              <p>Starts from an empty circuit and grows it one operator at a time. At each step it measures the parameter-shift gradient of every operator in the UCCSD excitation pool and appends only the one with the largest gradient, then re-optimises. The result is a small, problem-tailored subset of the UCCSD pool rather than the full excitation set.</p>
              <p className="text-emerald-700 dark:text-emerald-400 font-medium">Why it matters for medium molecules:</p>
              <p>Full UCCSD on molecules like H₂CO, C₄H₆, H₆ and benzene carries hundreds of parameters — more than COBYLA can navigate in a tractable number of iterations. ADAPT-VQE reaches the same accuracy class with a fraction of the parameters, and is what certifies these systems on the leaderboard.</p>
              <p className="text-amber-700 dark:text-amber-400 font-medium">Circuit metrics:</p>
              <p>ADAPT builds from the same exponential Pauli operators as UCCSD, so depth and 2Q gate counts are symbolic until compiled for a hardware target and may show &ldquo;—&rdquo; for the same reason.</p>
            </div>
          </div>
          <p className="text-muted-foreground/70 border-t pt-3">
            All energies are computed on a classical simulator (PennyLane + NumPy backend) with exact statevector simulation — no shot noise. Circuit metrics refer to the pre-simulation ansatz structure.
          </p>
        </div>
      </details>
    </div>
  );
}
