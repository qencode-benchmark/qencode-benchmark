import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="container py-24 max-w-2xl text-center">
      <p className="text-sm font-medium text-primary mb-3 uppercase tracking-wide">404</p>
      <h1 className="text-3xl sm:text-4xl font-bold mb-4">Page not found</h1>
      <p className="text-muted-foreground mb-8">
        The page you requested does not exist or has moved.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Button asChild>
          <Link href="/">Back to Home</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/pricing">View Pricing</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/apply">Apply for Access</Link>
        </Button>
      </div>
    </div>
  );
}

