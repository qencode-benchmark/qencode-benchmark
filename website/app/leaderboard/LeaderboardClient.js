"use client";

import { useMemo, useState } from "react";
import {
  CheckCircle, Copy, Check, Crown, Info, TrendingDown, Cpu, BarChart2,
} from "lucide-react";
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
          ? "bg-[#185FA5] text-white border-[#185FA5]"
          : "bg-background text-muted-foreground border-border hover:border-[#185FA5] hover:text-foreground"}
      `}
    >
      {label}
    </button>
  );
}

// ── Main table renderer ────────────────────────────────────────────────────────

function LeaderboardTable({ rows, category }) {
  const includeBalanced = category === "balanced";
  const includeHardware = category === "cost" || category === "balanced";

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
                      <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs text-xs">
                      |E_vqe − E_fci| in Hartrees. Chemical accuracy = 1.6 × 10⁻³ Ha.
                      Lower is better.
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              </span>
            </TableHead>
            <TableHead className="w-20"></TableHead>
            {includeHardware && (
              <>
                <TableHead className="text-right">2Q Gates</TableHead>
                <TableHead className="text-right">Depth</TableHead>
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
            const configStr = `${r.molecule.toLowerCase()}-${r.mapping}-${r.ansatz}-v1`;
            return (
              <TableRow
                key={`${r.molecule}-${r.mapping}-${r.ansatz}-${idx}`}
                className={`hover:bg-muted/30 transition-colors ${isFirst ? "bg-amber-50/40 dark:bg-amber-950/10" : ""}`}
              >
                {/* Rank */}
                <TableCell className="text-center">
                  {isFirst ? (
                    <span className="inline-flex items-center justify-center">
                      <Crown className="h-4 w-4 text-amber-500" />
                    </span>
                  ) : (
                    <span className="font-mono text-sm text-muted-foreground">#{r.rank}</span>
                  )}
                </TableCell>

                {/* Molecule */}
                <TableCell>
                  <span className="font-mono text-sm font-medium">
                    {r.molecule}
                  </span>
                </TableCell>

                {/* Mapping */}
                <TableCell>
                  <span className="text-xs text-muted-foreground">
                    {mappingLabel(r.mapping)}
                  </span>
                </TableCell>

                {/* Ansatz */}
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-muted-foreground">{ansatzLabel(r.ansatz)}</span>
                    <CopyConfig text={configStr} />
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

                {/* Hardware columns */}
                {includeHardware && (
                  <>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {fmtInt(r.twoQ)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {fmtInt(r.depth)}
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
                  {r.baseline ? (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge className="bg-[#185FA5] text-white text-xs gap-1 cursor-help">
                            <CheckCircle className="h-3 w-3" /> Baseline
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
                      <CheckCircle className="h-3 w-3 text-green-500" /> Verified
                    </Badge>
                  )}
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

export default function LeaderboardClient({ acc, cost, balanced, research = [] }) {
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

  const filteredAcc      = useMemo(() => applyFilters(acc), [acc, molecule, activeMappings, activeAnsatze]);
  const filteredCost     = useMemo(() => applyFilters(cost).filter((r) => r.twoQ != null && r.depth != null), [cost, molecule, activeMappings, activeAnsatze]);
  const filteredBalanced = useMemo(() => applyFilters(balanced).filter((r) => r.twoQ != null && r.depth != null), [balanced, molecule, activeMappings, activeAnsatze]);
  const filteredResearch = useMemo(() => applyFilters(research), [research, molecule, activeMappings, activeAnsatze]);

  const totalVisible = filteredAcc.length + filteredCost.length + filteredBalanced.length;

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

        {/* Active count */}
        <div className="flex items-center justify-between pt-1 border-t">
          <p className="text-xs text-muted-foreground">
            Showing {totalVisible} entries across all categories
          </p>
          <button
            onClick={() => {
              setMolecule("All");
              setActiveMappings(new Set(mappings));
              setActiveAnsatze(new Set(ansatze));
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
            <TrendingDown className="h-3.5 w-3.5" />
            Best Accuracy
            <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-mono">
              {filteredAcc.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="cost" className="flex items-center gap-1.5">
            <Cpu className="h-3.5 w-3.5" />
            Lowest Cost
            <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-mono">
              {filteredCost.length}
            </span>
          </TabsTrigger>
          <TabsTrigger value="balanced" className="flex items-center gap-1.5">
            <BarChart2 className="h-3.5 w-3.5" />
            Balanced
            <span className="ml-1 rounded-full bg-muted px-1.5 py-0.5 text-xs font-mono">
              {filteredBalanced.length}
            </span>
          </TabsTrigger>
          {filteredResearch.length > 0 && (
            <TabsTrigger value="research" className="flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5" />
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
              Ranked by lowest |E<sub>VQE</sub> − E<sub>FCI</sub>| error gap. Chemical accuracy threshold: 1.6 × 10⁻³ Ha.
            </p>
          </div>
          <LeaderboardTable rows={filteredAcc} category="accuracy" />
        </TabsContent>

        <TabsContent value="cost" className="mt-6">
          <div className="mb-3">
            <h3 className="text-sm font-medium text-foreground">Lowest Hardware Cost</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Ranked by fewest two-qubit gates (then circuit depth). Entries without transpiled metrics are excluded.
            </p>
          </div>
          <LeaderboardTable rows={filteredCost} category="cost" />
        </TabsContent>

        <TabsContent value="balanced" className="mt-6">
          <div className="mb-3">
            <h3 className="text-sm font-medium text-foreground">Balanced Score</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Combined score weighting accuracy and hardware cost equally. Lower is better.
            </p>
          </div>
          <LeaderboardTable rows={filteredBalanced} category="balanced" />
        </TabsContent>

        {filteredResearch.length > 0 && (
          <TabsContent value="research" className="mt-6">
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
              <h3 className="text-sm font-semibold text-amber-900 flex items-center gap-1.5">
                <Info className="h-4 w-4" />
                Advanced Benchmark — Research Tier
              </h3>
              <p className="text-xs text-amber-800 mt-1">
                These entries are <strong>validated</strong> but do not meet the 0.01 Ha certification threshold.
                They represent strongly-correlated systems (e.g. N₂ with a [6,6] active space) where
                standard UCCSD-reps-1 reaches its physical limit. Results are reproducible and correct —
                the gap reflects the method&apos;s limitation, not an implementation error.
              </p>
            </div>
            <LeaderboardTable rows={filteredResearch} category="research" />
          </TabsContent>
        )}
      </Tabs>

      {/* ── Legend ─────────────────────────────────────────────────────────── */}
      <div className="rounded-lg border bg-muted/10 p-4">
        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">Legend</p>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Crown className="h-3.5 w-3.5 text-amber-500" /> Rank #1 in category
          </span>
          <span className="flex items-center gap-1.5">
            <Badge className="bg-[#185FA5] text-white text-xs">Baseline</Badge>
            Run by QEncode team
          </span>
          <span className="flex items-center gap-1.5">
            <Badge variant="secondary" className="text-xs">Verified</Badge>
            Community submission
          </span>
          <span className="flex items-center gap-1.5">
            <div className="w-10 h-1.5 bg-muted rounded-full overflow-hidden">
              <div className="h-full w-1/4 bg-green-500 rounded-full" />
            </div>
            Relative gap (log scale, green = best)
          </span>
        </div>
      </div>
    </div>
  );
}
