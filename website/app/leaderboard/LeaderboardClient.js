"use client";

import { useMemo, useState } from "react";
import { CheckCircle, Copy, Check } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

function CopyConfig({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      className="inline-flex items-center gap-1.5 font-mono text-sm hover:text-primary transition-colors group"
    >
      {text}
      {copied ? <Check className="h-3 w-3 text-verified" /> : <Copy className="h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />}
    </button>
  );
}

function table(rows, includeBalanced = false) {
  return (
    <div className="rounded-lg border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-16">Rank</TableHead>
            <TableHead>Configuration</TableHead>
            <TableHead className="text-right">Error Gap</TableHead>
            <TableHead className="text-right">Gates</TableHead>
            <TableHead className="text-right">Depth</TableHead>
            {includeBalanced ? <TableHead className="text-right">Balanced</TableHead> : null}
            <TableHead className="text-right">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, idx) => (
            <TableRow key={`${r.molecule}-${r.mapping}-${r.ansatz}-${idx}`} className="hover:bg-muted/30">
              <TableCell className="font-mono font-semibold text-muted-foreground">#{r.rank}</TableCell>
              <TableCell><CopyConfig text={`${r.molecule.toLowerCase()}-${r.mapping}-${r.ansatz}-v1`} /></TableCell>
              <TableCell className="text-right font-mono text-sm">{r.gap?.toFixed ? r.gap.toFixed(6) : r.gap}</TableCell>
              <TableCell className="text-right font-mono text-sm">{r.twoQ}</TableCell>
              <TableCell className="text-right font-mono text-sm">{r.depth}</TableCell>
              {includeBalanced ? <TableCell className="text-right font-mono text-sm">{r.balancedScore?.toFixed ? r.balancedScore.toFixed(6) : r.balancedScore}</TableCell> : null}
              <TableCell className="text-right">
                {r.baseline ? (
                  <Badge className="bg-verified text-white text-xs gap-1">
                    <CheckCircle className="h-3 w-3" /> Baseline
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="text-xs">Verified</Badge>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export default function LeaderboardClient({ acc, cost, balanced }) {
  const molecules = useMemo(() => {
    const set = new Set([...acc, ...cost, ...balanced].map((r) => r.molecule));
    return ["All", ...Array.from(set).sort()];
  }, [acc, cost, balanced]);

  const [molecule, setMolecule] = useState((molecules.find((m) => m !== "All")) || "All");

  const f = (rows) => rows.filter((r) => molecule === "All" || r.molecule === molecule);

  return (
    <div>
      <Tabs value={molecule} onValueChange={setMolecule}>
        <TabsList className="mb-6">
          {molecules.filter((m) => m !== "All").map((m) => (
            <TabsTrigger key={m} value={m} className="font-mono">{m}</TabsTrigger>
          ))}
        </TabsList>
        {molecules.filter((m) => m !== "All").map((m) => (
          <TabsContent key={m} value={m}>
            <div className="space-y-8">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Best Accuracy</h3>
                {table(f(acc))}
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Lowest Hardware Cost</h3>
                {table(f(cost))}
              </div>
              <div>
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide mb-3">Best Balanced Score</h3>
                {table(f(balanced), true)}
              </div>
            </div>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}

