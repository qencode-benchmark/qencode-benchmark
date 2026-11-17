import Link from "next/link";
import { CheckCircle2, GraduationCap, Scale } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Free managed certification for open academic research, plus the rule that payment
 * never changes the outcome. Shared by /pricing and /certify so the two pages cannot
 * drift apart.
 *
 * The free tier is defined by what happens to the results (published openly on the
 * leaderboard), not by who the applicant is, so it is easy to check and every free run
 * becomes a public entry.
 */
export function OpenResearchTier({ trackPrefix = "pricing" }) {
  return (
    <section className="rounded-lg border border-verified/40 bg-verified/5 p-6 mb-8">
      <div className="flex items-center gap-2 mb-1">
        <GraduationCap className="h-5 w-5 text-verified shrink-0" />
        <h2 className="font-semibold text-lg">Open research — free</h2>
      </div>
      <p className="text-sm text-muted-foreground mb-4 max-w-2xl">
        For researchers at universities, public research institutes and non-profits whose results
        will be published openly. Same managed run, same signed entry and report as the paid plans.
      </p>
      <ul className="space-y-2 text-sm text-muted-foreground mb-5">
        <li className="flex gap-2">
          <CheckCircle2 className="h-4 w-4 mt-0.5 text-verified shrink-0" />
          Managed run of Suite v4 molecules, Ed25519-signed entry and validation report.
        </li>
        <li className="flex gap-2">
          <CheckCircle2 className="h-4 w-4 mt-0.5 text-verified shrink-0" />
          Results are published on the public leaderboard, including runs that do not pass
          (they appear in the research tier).
        </li>
        <li className="flex gap-2">
          <CheckCircle2 className="h-4 w-4 mt-0.5 text-verified shrink-0" />
          Limited places each month, by application.
        </li>
      </ul>
      <Button asChild>
        <Link href="/apply?type=academic" data-track={`${trackPrefix}_academic_apply`}>
          Apply for open research
        </Link>
      </Button>
    </section>
  );
}

/** Payment buys the managed run and the report, never the result. */
export function SameCriteriaNote() {
  return (
    <section className="rounded-lg border p-5 mb-6">
      <div className="flex items-center gap-2 mb-2">
        <Scale className="h-4 w-4 text-primary shrink-0" />
        <h2 className="font-semibold">Same criteria for every run</h2>
      </div>
      <p className="text-sm text-muted-foreground">
        Payment covers the managed run, the audit work and the report — never the result. Free and
        paid runs are judged by the same public criteria: an energy gap below 10 mHa to the CASCI
        reference, computed with the pinned pipeline and signed. A run that misses the threshold is
        reported as research tier, whether or not it was paid for.
      </p>
    </section>
  );
}
