"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Menu, X } from "lucide-react";
import { SignedIn, SignedOut, UserButton } from "@clerk/nextjs";

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
        <Link href="/" className="flex flex-col leading-tight">
          <span className="flex items-center gap-2 font-semibold text-lg tracking-tight">
            <span className="font-mono text-primary">Q</span>Encode
          </span>
          <span className="text-[12px] text-muted-foreground">Benchmark Standard</span>
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
          <SignedIn>
            <Link
              href="/dashboard"
              data-track="nav_dashboard"
              className={cn("text-sm font-medium transition-colors hover:text-foreground text-muted-foreground")}
            >
              Dashboard
            </Link>
          </SignedIn>
        </nav>
        <div className="hidden md:flex items-center gap-3">
          <SignedOut>
            <Link
              href="/sign-in"
              data-track="nav_sign_in"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/apply"
              data-track="nav_apply_for_access"
              className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-95 transition-opacity"
            >
              Apply for Access
            </Link>
          </SignedOut>
          <SignedIn>
            <Link
              href="/pricing"
              data-track="nav_certify"
              className="inline-flex items-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-95 transition-opacity"
            >
              Certify
            </Link>
            <UserButton afterSignOutUrl="/" />
          </SignedIn>
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
            <SignedIn>
              <Link
                href="/dashboard"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_dashboard"
                className={cn(
                  "px-2 py-2 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-foreground text-muted-foreground"
                )}
              >
                Dashboard
              </Link>
            </SignedIn>
            <SignedOut>
              <Link
                href="/sign-in"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_sign_in"
                className={cn(
                  "px-2 py-2 rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-foreground text-muted-foreground"
                )}
              >
                Sign in
              </Link>
              <Link
                href="/apply"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_apply_for_access"
                className="mt-2 inline-flex items-center justify-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-95 transition-opacity"
              >
                Apply for Access
              </Link>
            </SignedOut>
            <SignedIn>
              <Link
                href="/pricing"
                onClick={() => setOpen(false)}
                data-track="nav_mobile_certify"
                className="mt-2 inline-flex items-center justify-center rounded-md bg-[#185FA5] px-4 py-2 text-sm font-medium text-white hover:opacity-95 transition-opacity"
              >
                Certify
              </Link>
            </SignedIn>
          </nav>
        </div>
      )}
    </header>
  );
}
