import Link from "next/link";
import { ArrowRight, BarChart3, Shield, Trophy, Database, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function HomePage() {
  const REPO_URL = "https://github.com/jlabanimation-del/qencode-benchmark-suite";
  const solutions = [
    { icon: BarChart3, title: "Standard Benchmark Suite", desc: "Fixed molecule, encoding, and ansatz configurations" },
    { icon: Shield, title: "Certified Results", desc: "Verified outputs with reproducibility guarantees" },
    { icon: Trophy, title: "Leaderboard Rankings", desc: "Compare algorithms across accuracy and cost" },
    { icon: Database, title: "Reproducible Datasets", desc: "Open data for every benchmark run" }
  ];
  const steps = [
    { num: "01", title: "Install QEncode", desc: "Install CLI and benchmark tooling." },
    { num: "02", title: "Run benchmark suite", desc: "Execute fixed, reproducible suite jobs." },
    { num: "03", title: "Generate results", desc: "Produce certified-only leaderboard dataset." },
    { num: "04", title: "Explore leaderboard", desc: "Compare mappings and ansatzes quickly." }
  ];
  const exampleRows = [
    { rank: 1, config: "qenc-h2-jw-uccsd-v1", gap: "1.15e-09", gates: 56, status: "verified" },
    { rank: 2, config: "qenc-h2-parity-uccsd-v1", gap: "7.67e-09", gates: 1, status: "verified" },
    { rank: 3, config: "qenc-h2-bk-uccsd-v1", gap: "1.44e-08", gates: 38, status: "verified" },
    { rank: 4, config: "qenc-h2-bk-hea-v1", gap: "2.24e-03", gates: 12, status: "verified" }
  ];

  return (
    <div className="min-h-screen">
      <section className="container py-24 lg:py-32">
        <p className="text-sm font-medium text-primary mb-4 tracking-wide uppercase">Quantum Algorithm Benchmarking</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1] mb-6">
          The Standard for Quantum Algorithm Benchmarking.
        </h1>
        <p className="text-lg text-muted-foreground max-w-xl mb-8">
          Run standardized benchmarks. Compare algorithms. Reproduce results.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/leaderboard">View Leaderboard <ArrowRight className="ml-1 h-4 w-4" /></Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer">Run Benchmark</a>
          </Button>
        </div>
      </section>

      <section className="border-t bg-muted/40">
        <div className="container py-20">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">Quantum algorithm benchmarking is inconsistent.</h2>
          <p className="text-muted-foreground text-lg max-w-2xl">
          Different studies use different configurations, making results hard to compare and reproduce.
          Without a standard, progress is difficult to measure.
          </p>
        </div>
      </section>

      <section className="container py-20">
        <h2 className="text-2xl sm:text-3xl font-bold mb-10">QEncode provides</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {solutions.map((s) => (
            <Card key={s.title} className="h-full border bg-card hover:shadow-md transition-shadow">
              <CardContent className="pt-6">
                <s.icon className="h-5 w-5 text-primary mb-3" />
                <h3 className="font-semibold mb-1">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.desc}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="border-t bg-muted/40">
        <div className="container py-20">
          <h2 className="text-2xl sm:text-3xl font-bold mb-10">How it works</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((s) => (
              <div key={s.num}>
                <span className="font-mono text-4xl font-bold text-primary/20">{s.num}</span>
                <h3 className="font-semibold mt-2 mb-1">{s.title}</h3>
                <p className="text-sm text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
          <div className="mt-10">
            <div className="inline-block rounded-lg bg-foreground text-background px-4 py-3 font-mono text-sm">
              <span className="text-muted-foreground select-none">$ </span>pip install qencode
            </div>
          </div>
        </div>
      </section>

      <section className="container py-20">
        <div className="flex items-center gap-3 mb-6">
          <h2 className="text-2xl sm:text-3xl font-bold">Example Leaderboard</h2>
          <Badge variant="secondary" className="text-xs font-mono">H2</Badge>
        </div>
        <div className="rounded-lg border overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="w-16">Rank</TableHead>
                <TableHead>Configuration</TableHead>
                <TableHead className="text-right">Error Gap</TableHead>
                <TableHead className="text-right">Gate Count</TableHead>
                <TableHead className="text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {exampleRows.map((row) => (
                <TableRow key={row.rank} className="hover:bg-muted/30">
                  <TableCell className="font-mono font-semibold text-muted-foreground">#{row.rank}</TableCell>
                  <TableCell className="font-mono text-sm">{row.config}</TableCell>
                  <TableCell className="text-right font-mono text-sm">{row.gap}</TableCell>
                  <TableCell className="text-right font-mono text-sm">{row.gates}</TableCell>
                  <TableCell className="text-right">
                    <Badge className="bg-verified text-white text-xs gap-1">
                      <CheckCircle className="h-3 w-3" /> Verified
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </section>

      <section className="border-t bg-muted/40">
        <div className="container py-20 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">Start benchmarking your algorithm today</h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Join the growing community of researchers using QEncode to standardize quantum algorithm evaluation.
          </p>
          <div className="flex justify-center gap-3">
            <Button asChild size="lg"><Link href="/leaderboard">Leaderboard</Link></Button>
            <Button asChild variant="outline" size="lg">
              <a href={`${REPO_URL}#quick-start`} target="_blank" rel="noopener noreferrer">Quick Start</a>
            </Button>
          </div>
        </div>
      </section>
      <div className="h-4" />
      <div className="container">
        <p className="text-xs text-muted-foreground">Data is loaded from the public release dataset.</p>
      </div>
    </div>
  );
}

