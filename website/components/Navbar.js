"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";

const links = [
  { to: "/leaderboard", label: "Leaderboard" },
  { to: "/benchmark", label: "Benchmark" },
  { to: "/pricing", label: "Pricing" },
  { to: "/blog", label: "Blog" },
  { to: "/docs", label: "Docs" },
  { to: "/about", label: "About" }
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between">
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
        <nav className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <Link
              key={l.to}
              href={l.to}
              data-track={`nav_${l.label.toLowerCase().replace(/\s+/g, "_")}`}
              className={cn("text-sm font-medium transition-colors hover:text-foreground text-muted-foreground")}
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/apply"
            data-track="nav_apply_for_access"
            className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-95 transition-opacity"
          >
            Apply for Access
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-md border border-input text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          aria-label="Toggle navigation menu"
          aria-expanded={open}
          aria-controls="mobile-nav-menu"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </div>

      {open && (
        <div id="mobile-nav-menu" className="md:hidden border-t bg-background">
          <nav className="container py-3 flex flex-col gap-1">
            {links.map((l) => (
              <Link
                key={l.to}
                href={l.to}
                onClick={() => setOpen(false)}
                data-track={`nav_mobile_${l.label.toLowerCase().replace(/\s+/g, "_")}`}
                className={cn(
                  "px-2 py-2 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-foreground text-muted-foreground"
                )}
              >
                {l.label}
              </Link>
            ))}
            <Link
                href="/apply"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_apply_for_access"
                className="mt-2 inline-flex items-center justify-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-95 transition-opacity"
              >
                Apply for Access
              </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
