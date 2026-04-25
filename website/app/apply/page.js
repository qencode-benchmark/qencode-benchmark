"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SUPPORT_EMAIL = "support@qencode-benchmark.org";

export default function ApplyPage() {
  const [form, setForm] = useState({
    company: "",
    contactName: "",
    workEmail: "",
    role: "",
    moleculeScope: "",
    timeline: "",
    monthlyRuns: "",
    needsCertification: "yes",
    needsPrivateBenchmark: "yes",
    notes: "",
  });

  const [status, setStatus] = useState("idle"); // idle | submitting | success | error
  const [errorMsg, setErrorMsg] = useState("");

  const recommendation = useMemo(() => {
    const runs = Number(form.monthlyRuns || 0);
    if (runs >= 40) return "Enterprise";
    if (runs >= 10) return "Team";
    return "Starter";
  }, [form.monthlyRuns]);

  function updateField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus("submitting");
    setErrorMsg("");

    try {
      const res = await fetch("/api/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, recommendation }),
      });

      const data = await res.json();

      if (!res.ok) {
        setErrorMsg(data?.error || "Something went wrong. Please try again.");
        setStatus("error");
        return;
      }

      setStatus("success");
    } catch {
      setErrorMsg("Network error. Please check your connection and try again.");
      setStatus("error");
    }
  }

  // ── Success state ───────────────────────────────────────────────────────────
  if (status === "success") {
    return (
      <div className="container py-16 max-w-3xl">
        <Card className="border max-w-xl mx-auto">
          <CardContent className="pt-8 pb-8 flex flex-col items-center text-center gap-4">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-verified/15 text-verified">
              <CheckCircle2 className="h-7 w-7" />
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-2">Application submitted</h2>
              <p className="text-sm text-muted-foreground max-w-sm">
                We&apos;ve received your application for <strong className="text-foreground">{form.company}</strong> and
                sent a confirmation to <strong className="text-foreground">{form.workEmail}</strong>.
              </p>
            </div>
            <div className="flex items-start gap-3 rounded-md border p-3 text-left text-sm w-full">
              <Mail className="h-4 w-4 mt-0.5 text-primary shrink-0" />
              <div>
                <p className="font-medium text-foreground">What happens next</p>
                <p className="text-muted-foreground mt-0.5">
                  Our team reviews your application and responds within 1–2 business days with access
                  scope and recommended plan.
                </p>
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <Button asChild variant="outline">
                <Link href="/leaderboard">View Leaderboard</Link>
              </Button>
              <Button asChild variant="ghost">
                <Link href="/pricing">See Pricing</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ── Form ────────────────────────────────────────────────────────────────────
  return (
    <div className="container py-16 max-w-3xl">
      <h1 className="text-3xl sm:text-4xl font-bold mb-3">Apply for Access</h1>
      <p className="text-muted-foreground mb-8">
        Share your workload and goals. We review each request and respond with access scope, expected
        timeline, and recommended plan.
      </p>
      <p className="text-sm rounded-md border bg-muted/40 px-3 py-2 mb-8">
        Early access is free for qualifying teams.
      </p>

      <Card className="border">
        <CardHeader>
          <CardTitle>Qualification form</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1">
                <span className="text-muted-foreground">Company/Lab *</span>
                <input
                  required
                  className="w-full rounded-md border bg-background px-3 py-2"
                  value={form.company}
                  onChange={(e) => updateField("company", e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Primary Contact *</span>
                <input
                  required
                  className="w-full rounded-md border bg-background px-3 py-2"
                  value={form.contactName}
                  onChange={(e) => updateField("contactName", e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Work Email *</span>
                <input
                  required
                  type="email"
                  className="w-full rounded-md border bg-background px-3 py-2"
                  value={form.workEmail}
                  onChange={(e) => updateField("workEmail", e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Role</span>
                <input
                  className="w-full rounded-md border bg-background px-3 py-2"
                  value={form.role}
                  onChange={(e) => updateField("role", e.target.value)}
                />
              </label>
              <label className="space-y-1 sm:col-span-2">
                <span className="text-muted-foreground">Molecule Scope *</span>
                <input
                  required
                  className="w-full rounded-md border bg-background px-3 py-2"
                  placeholder="Example: H2, LiH, N2, custom set"
                  value={form.moleculeScope}
                  onChange={(e) => updateField("moleculeScope", e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Target Timeline *</span>
                <input
                  required
                  className="w-full rounded-md border bg-background px-3 py-2"
                  placeholder="Example: 2–4 weeks"
                  value={form.timeline}
                  onChange={(e) => updateField("timeline", e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Estimated Runs / Month</span>
                <input
                  type="number"
                  min="0"
                  className="w-full rounded-md border bg-background px-3 py-2"
                  placeholder="Example: 12"
                  value={form.monthlyRuns}
                  onChange={(e) => updateField("monthlyRuns", e.target.value)}
                />
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Need Certification?</span>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2"
                  value={form.needsCertification}
                  onChange={(e) => updateField("needsCertification", e.target.value)}
                >
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </label>
              <label className="space-y-1">
                <span className="text-muted-foreground">Need Private Benchmarking?</span>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2"
                  value={form.needsPrivateBenchmark}
                  onChange={(e) => updateField("needsPrivateBenchmark", e.target.value)}
                >
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                </select>
              </label>
              <label className="space-y-1 sm:col-span-2">
                <span className="text-muted-foreground">Notes</span>
                <textarea
                  className="w-full rounded-md border bg-background px-3 py-2 min-h-[100px]"
                  value={form.notes}
                  onChange={(e) => updateField("notes", e.target.value)}
                />
              </label>
            </div>

            <div className="rounded-md border bg-muted/40 p-3 text-muted-foreground">
              <span className="font-medium text-foreground">Auto recommendation:</span>{" "}
              {recommendation}
            </div>

            {status === "error" && (
              <p className="text-sm text-red-500">{errorMsg}</p>
            )}

            <div className="pt-1 flex flex-wrap gap-3">
              <Button
                type="submit"
                disabled={status === "submitting"}
                data-track="apply_submit_application"
              >
                {status === "submitting" ? "Submitting…" : "Submit Application"}
              </Button>
              <Button asChild variant="outline">
                <Link href="/pricing" data-track="apply_view_pricing">View Pricing</Link>
              </Button>
              <Button asChild variant="ghost">
                <a href={`mailto:${SUPPORT_EMAIL}`} data-track="apply_email_support_direct">
                  Email Support Directly
                </a>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
