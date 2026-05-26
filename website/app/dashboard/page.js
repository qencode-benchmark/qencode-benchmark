import Link from "next/link";
import { BarChart3, BookOpen, Github, FlaskConical, Mail } from "lucide-react";

export const metadata = {
  title: "Dashboard | QEncode",
  description: "Your QEncode starting point — leaderboard, docs, benchmark spec, and certification status.",
};

const quickLinks = [
  {
    icon: BarChart3,
    title: "Leaderboard",
    desc: "View certified results across all Suite v4 molecules.",
    href: "/leaderboard",
    external: false,
  },
  {
    icon: BookOpen,
    title: "Benchmark Spec",
    desc: "Suite v4 molecules, qubit counts, encodings, and ansatz definitions.",
    href: "/benchmark",
    external: false,
  },
  {
    icon: FlaskConical,
    title: "Methodology",
    desc: "Full pipeline: PySCF → CASSCF → CASCI → PennyLane → VQE → signing.",
    href: "/methodology",
    external: false,
  },
  {
    icon: Github,
    title: "GitHub Repository",
    desc: "Source code, requirements-v4.txt, all certified entry JSON files.",
    href: "https://github.com/qencode-benchmark/qencode-benchmark",
    external: true,
  },
];

export default function DashboardPage() {
  return (
    <div className="container py-16 max-w-3xl">
      <Link href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors mb-8 inline-block">
        ← Back to QEncode
      </Link>

      <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
      <p className="text-muted-foreground mb-10">
        Order tracking and account management are coming in a future release.
        In the meantime, everything you need is linked below.
      </p>

      <div className="grid sm:grid-cols-2 gap-4 mb-10">
        {quickLinks.map((item) => (
          item.external ? (
            <a
              key={item.title}
              href={item.href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-4 rounded-lg border p-5 hover:shadow-md hover:border-primary/30 transition-all"
            >
              <item.icon className="h-5 w-5 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-sm">{item.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
              </div>
            </a>
          ) : (
            <Link
              key={item.title}
              href={item.href}
              className="flex items-start gap-4 rounded-lg border p-5 hover:shadow-md hover:border-primary/30 transition-all"
            >
              <item.icon className="h-5 w-5 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="font-semibold text-sm">{item.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
              </div>
            </Link>
          )
        ))}
      </div>

      <div className="rounded-lg border p-5 text-sm">
        <div className="flex items-start gap-3">
          <Mail className="h-4 w-4 mt-0.5 text-primary shrink-0" />
          <div>
            <p className="font-medium mb-1">Check on a certification order</p>
            <p className="text-muted-foreground">
              Contact us with your order details and we&apos;ll respond within 1 business day.
            </p>
            <a
              href="mailto:support@qencode-benchmark.org"
              className="inline-flex items-center mt-2 text-primary hover:underline"
            >
              support@qencode-benchmark.org
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
