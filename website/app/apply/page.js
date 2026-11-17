"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CheckCircle2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SUPPORT_EMAIL = "support@qencode-benchmark.org";
const APPLICANT_TYPES = ["academic", "commercial"];

export default function ApplyPage() {
  const [form, setForm] = useState({
    applicantType: "",
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

  const isAcademic = form.applicantType === "academic";

  // Pre-select the applicant type from the link that brought the visitor here
  // (/apply?type=academic from the open-research card, ?type=commercial from a paid plan).
  useEffect(() => {
    const type = new URLSearchParams(window.location.search).get("type");
    if (APPLICANT_TYPES.includes(type)) {
      setForm((prev) => ({ ...prev, applicantType: type, ...(type === "academic" ? { needsPrivateBenchmark: "no" } : {}) }));
    }
  }, []);

  const recommendation = useMemo(() => {
    if (isAcademic) return "Open research (free)";
    const runs = Number(form.monthlyRuns || 0);
    if (runs >= 40) return "Enterprise";
    if (runs >= 10) return "Team";
    return "Starter";
  }, [form.monthlyRuns, isAcademic]);

  function selectApplicantType(type) {
    // The free tier publishes results openly, so private benchmarking does not apply to it.
    setForm((prev) => ({
      ...prev,
      applicantType: type,
      needsPrivateBenchmark: type === "academic" ? "no" : prev.needsPrivateBenchmark,
    }));
  }

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
      <h1 className="text-3xl sm:text-4xl font-bold mb-3">Apply for Certification</h1>
      <p className="text-muted-foreground mb-3">
        The QEncode benchmark suite is free and open source — clone the repo and run it yourself anytime.
        Use this form if you need <strong className="text-foreground">managed certification</strong>: a signed
        artifact, audit-ready report, and leaderboard inclusion for papers, grants, or hardware evaluations.
        It is <strong className="text-foreground">free for open academic research</strong>; companies and
        private results use the <Link href="/pricing" className="text-primary hover:underline">paid plans</Link>.
      </p>
      <p className="text-sm rounded-md border bg-muted/40 px-3 py-2 mb-8">
        Tell us your molecule scope, timeline, and what you need the output for. We respond within 1–2 business days.
      </p>

      <Card className="border">
        <CardHeader>
          <CardTitle>Certification request</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <fieldset className="space-y-2">
              <legend className="text-muted-foreground mb-1">Applying as *</legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {[
                  {
                    value: "academic",
                    title: "Open academic research — free",
                    desc: "University, public institute or non-profit. Results published openly on the leaderboard.",
                  },
                  {
                    value: "commercial",
                    title: "Company or private results — paid",
                    desc: "Commercial use, company-funded work, or results that stay private.",
                  },
                ].map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex gap-2 rounded-md border p-3 cursor-pointer ${
                      form.applicantType === opt.value ? "border-primary bg-primary/5" : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="applicantType"
                      value={opt.value}
                      required
                      checked={form.applicantType === opt.value}
                      onChange={() => selectApplicantType(opt.value)}
                      className="mt-1"
                    />
                    <span>
                      <span className="font-medium text-foreground block">{opt.title}</span>
                      <span className="text-muted-foreground text-xs">{opt.desc}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

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
                <span className="text-muted-foreground">Number of molecules needed</span>
                <input
                  type="number"
                  min="0"
                  className="w-full rounded-md border bg-background px-3 py-2"
                  placeholder="Example: 3"
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
              {isAcademic ? (
                <p className="text-xs text-muted-foreground self-end pb-2">
                  Open-research results are published on the leaderboard, including runs that do not
                  pass. Need them private? Choose the paid option.
                </p>
              ) : (
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
              )}
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
              <span className="font-medium text-foreground">Suggested plan:</span>{" "}
              {isAcademic
                ? "Open research — free (limited places each month; results published on the leaderboard)"
                : recommendation === "Starter" || recommendation === "Team"
                ? "Single molecule ($1,500) or Full Suite v4 ($4,000)"
                : "Full Suite v4 or Enterprise — we'll scope with you"
              }
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
