import Link from "next/link";
import { cn } from "@/lib/utils";
import { Github } from "lucide-react";

const links = [
  { to: "/leaderboard", label: "Leaderboard" },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/docs", label: "Docs" },
  { to: "/about", label: "About" }
];

export default function Navbar() {
  const REPO_URL = "https://github.com/jlabanimation-del/qencode-benchmark-suite";
  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
      <div className="container flex h-14 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold text-lg tracking-tight">
          <span className="font-mono text-primary">Q</span>Encode
        </Link>
        <nav className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <Link
              key={l.to}
              href={l.to}
              className={cn("text-sm font-medium transition-colors hover:text-foreground text-muted-foreground")}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden md:flex items-center gap-2">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-input text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            aria-label="GitHub repository"
            title="GitHub repository"
          >
            <Github className="h-4 w-4" />
          </a>
          <Link
            href="/leaderboard"
            className="inline-flex h-8 items-center rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            View Leaderboard
          </Link>
        </div>
      </div>
    </header>
  );
}

