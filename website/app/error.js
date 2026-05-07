"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Error({ error, reset }) {
  useEffect(() => {
    // Keep minimal logging for production diagnosis.
    console.error("App route error:", error);
  }, [error]);

  return (
    <div className="container py-24 max-w-2xl text-center">
      <p className="text-sm font-medium text-primary mb-3 uppercase tracking-wide">Something went wrong</p>
      <h1 className="text-3xl sm:text-4xl font-bold mb-4">We hit an unexpected error</h1>
      <p className="text-muted-foreground mb-8">
        Please try again. If the issue persists, contact support@qencode-benchmark.org.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Button onClick={() => reset()}>Try again</Button>
        <Button asChild variant="outline">
          <Link href="/">Go Home</Link>
        </Button>
        <Button asChild variant="outline">
          <a href="mailto:support@qencode-benchmark.org">Contact Support</a>
        </Button>
      </div>
    </div>
  );
}

