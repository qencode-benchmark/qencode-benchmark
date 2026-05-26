"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { Menu, X, Github } from "lucide-react";

const links = [
  { to: "/leaderboard",  label: "Leaderboard"  },
  { to: "/benchmark",    label: "Benchmark"     },
  { to: "/methodology",  label: "Methodology"   },
  { to: "/blog",         label: "Blog"          },
  { to: "/docs",         label: "Docs"          },
  { to: "/about",        label: "About"         },
];

const REPO_URL = "https://github.com/qencode-benchmark/qencode-benchmark";

export default function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between gap-4">

        {/* Logo */}
        <Link href="/" className="flex items-center shrink-0">
          <Image
            src="/logo.png"
            alt="QEncode Benchmark"
            width={44}
            height={44}
            className="h-11 w-auto"
            priority
          />
        </Link>

        {/* Desktop nav */}
        <nav className="hidden lg:flex items-center gap-5 flex-1">
          {links.map((l) => (
            <Link
              key={l.to}
              href={l.to}
              data-track={`nav_${l.label.toLowerCase().replace(/\s+/g, "_")}`}
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        {/* Desktop actions */}
        <div className="hidden lg:flex items-center gap-2 shrink-0">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            data-track="nav_github"
            className="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <Github className="h-4 w-4" />
            GitHub
          </a>
          <Link
            href="/apply"
            data-track="nav_get_started"
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Get Started
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="lg:hidden inline-flex h-10 w-10 items-center justify-center rounded-md border border-input text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          aria-controls="mobile-nav-menu"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div id="mobile-nav-menu" className="lg:hidden border-t bg-background">
          <nav className="container py-3 flex flex-col gap-1">
            {links.map((l) => (
              <Link
                key={l.to}
                href={l.to}
                onClick={() => setOpen(false)}
                data-track={`nav_mobile_${l.label.toLowerCase().replace(/\s+/g, "_")}`}
                className="px-2 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
              >
                {l.label}
              </Link>
            ))}
            <div className="mt-2 flex flex-col gap-2">
              <a
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_github"
                className="inline-flex items-center justify-center gap-1.5 rounded-md border px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              >
                <Github className="h-4 w-4" /> GitHub
              </a>
              <Link
                href="/apply"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_get_started"
                className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                Get Started
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
