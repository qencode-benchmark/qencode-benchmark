import Link from "next/link";
import Image from "next/image";
import { ArrowRight, BarChart3, Shield, Trophy, Database, CheckCircle, Clock3, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export const metadata = {
  title: "Quantum Algorithm Benchmarking Platform",
  description:
    "Benchmark quantum algorithms with QEncode's reproducible VQE suite, certification workflows, and public leaderboard for H2, BeH2, HF, LiH, and N2.",
  keywords: [
    "quantum algorithm benchmarking platform",
    "VQE leaderboard",
    "quantum benchmark suite",
    "quantum chemistry algorithm comparison"
  ],
  alternates: {
    canonical: "/"
  },
  openGraph: {
    title: "QEncode - Quantum Algorithm Benchmarking Platform",
    description:
      "Run reproducible VQE benchmarks, compare rankings, and certify quantum algorithm results with signed artifacts.",
    url: "/"
  },
  twitter: {
    title: "QEncode - Quantum Algorithm Benchmarking Platform",
    description:
      "Reproducible quantum algorithm benchmarks with certification and leaderboard ranking."
  }
};

export default function HomePage() {
  const solutions = [
    { icon: BarChart3, title: "Standard Benchmark Suite", desc: "Fixed molecule, encoding, and ansatz configurations" },
    { icon: Shield, title: "Certified Results", desc: "Verified outputs with reproducibility guarantees" },
    { icon: Trophy, title: "Leaderboard Rankings", desc: "Compare algorithms across accuracy and cost" },
    { icon: Database, title: "Reproducible Datasets", desc: "Open data for every benchmark run" }
  ];
  const steps = [
    { num: "01", title: "Apply for access", desc: "Tell us your molecule scope, timeline, and target outputs." },
    { num: "02", title: "Run managed benchmark", desc: "QEncode executes the fixed suite with controlled configuration." },
    { num: "03", title: "Receive signed artifacts", desc: "Get validation report and official signed certification receipt." },
    { num: "04", title: "Publish or keep private", desc: "Choose public leaderboard inclusion or private delivery only." }
  ];
  const exampleRows = [
    { rank: 1, config: "qenc-h2-jw-uccsd-v1", gap: "1.15e-09", gates: 56, status: "verified" },
    { rank: 2, config: "qenc-h2-parity-uccsd-v1", gap: "7.67e-09", gates: 38, status: "verified" },
    { rank: 3, config: "qenc-h2-bk-uccsd-v1", gap: "1.44e-08", gates: 38, status: "verified" },
    { rank: 4, config: "qenc-h2-bk-hea-v1", gap: "2.24e-03", gates: 12, status: "verified" }
  ];

  return (
    <div className="min-h-screen">
      <section className="container py-24 lg:py-32">
        <div className="mb-6 md:mb-8">
          <Image
            src="/logo.png"
            alt="QEncode Benchmark"
            width={160}
            height={160}
            className="h-24 md:h-40 w-auto"
            priority
          />
        </div>
        <p className="text-sm font-medium text-primary mb-4 tracking-wide uppercase">Quantum Algorithm Benchmarking Standard</p>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1] mb-6">
          The Standard for Quantum Algorithm Benchmarking.
        </h1>
        <p className="text-lg text-muted-foreground max-w-3xl mb-8">
          Quantum algorithm results are difficult to compare across papers and platforms. QEncode provides a fixed
          benchmark suite, managed execution, and signed certification artifacts so performance claims are reproducible
          and decision-ready.
        </p>
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg">
            <Link href="/apply" data-track="home_hero_apply">Apply for Access <ArrowRight className="ml-1 h-4 w-4" /></Link>
          </Button>
          <Button asChild variant="secondary" size="lg">
            <Link href="/pricing" data-track="home_hero_pricing">Pricing</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/leaderboard" data-track="home_hero_leaderboard">View Leaderboard</Link>
          </Button>
        </div>
        <div className="mt-8 flex flex-wrap gap-2">
          <Badge variant="secondary" className="text-xs">Suite v2</Badge>
          <Badge variant="secondary" className="text-xs">Signed Receipts</Badge>
          <Badge variant="secondary" className="text-xs">Certified Public Dataset</Badge>
        </div>
      </section>

      <section className="border-t bg-muted/40">
        <div className="container py-20">
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">Most benchmark claims are not directly comparable.</h2>
          <p className="text-muted-foreground text-lg max-w-2xl">
            Different molecule choices, encodings, ansatz settings, and runtime assumptions make cross-study comparison
            unreliable. Without a fixed benchmark standard, teams spend time arguing about setup rather than quality.
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
        </div>
      </section>

      <section className="container py-20">
        <h2 className="text-2xl sm:text-3xl font-bold mb-6">Pricing at a glance</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2"><Clock3 className="h-4 w-4 text-primary" /><h3 className="font-semibold">Single Molecule Certification</h3></div>
              <p className="text-3xl font-bold mb-2">$1,500</p>
              <p className="text-sm text-muted-foreground mb-4">Managed execution and signed certification for one Suite v2 molecule.</p>
              <Button asChild variant="outline"><Link href="/pricing" data-track="home_pricing_card_single">View details</Link></Button>
            </CardContent>
          </Card>
          <Card className="border">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 mb-2"><Lock className="h-4 w-4 text-primary" /><h3 className="font-semibold">Full Suite v2 Certification</h3></div>
              <p className="text-3xl font-bold mb-2">$4,000</p>
              <p className="text-sm text-muted-foreground mb-4">Full managed benchmark run, signed receipts, and audit-ready report package.</p>
              <Button asChild><Link href="/pricing" data-track="home_pricing_card_full">View details</Link></Button>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="container py-20">
        <div className="flex items-center gap-3 mb-6">
          <h2 className="text-2xl sm:text-3xl font-bold">Public Leaderboard Snapshot</h2>
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
          <h2 className="text-2xl sm:text-3xl font-bold mb-4">Ready to benchmark with certified reproducibility?</h2>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Start with a scoped access application. We align workload, timeline, and certification path with your
            target molecule set.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button asChild size="lg"><Link href="/apply" data-track="home_bottom_apply">Apply for Access</Link></Button>
            <Button asChild variant="secondary" size="lg"><Link href="/pricing" data-track="home_bottom_pricing">Pricing</Link></Button>
            <Button asChild variant="outline" size="lg">
              <Link href="/benchmark" data-track="home_bottom_benchmark_spec">Benchmark Spec</Link>
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

