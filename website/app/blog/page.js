import Link from "next/link";

export const metadata = {
  title: "Blog",
  description:
    "Technical articles on quantum algorithm benchmarking, VQE methodology, ansatz comparison, and reproducible quantum chemistry evaluation from the QEncode team.",
  alternates: { canonical: "/blog" },
  openGraph: {
    title: "QEncode Blog — Quantum Benchmarking Insights",
    description:
      "Technical articles on quantum algorithm benchmarking, VQE methodology, and reproducible quantum chemistry evaluation.",
    url: "https://www.qencode-benchmark.org/blog",
  },
};

const posts = [
  {
    slug: "uccsd-vs-hardware-efficient-ansatz",
    date: "2026-04-25",
    readingTime: "8 min read",
    title: "UCCSD vs Hardware-Efficient Ansatz: What the Benchmark Data Actually Shows",
    excerpt:
      "We ran both ansatz families across five molecules at three encodings and measured energy gap, circuit depth, and two-qubit gate count. Here's what the numbers say — and why the winner depends on what you're optimizing for.",
    tags: ["ansatz", "UCCSD", "benchmark", "VQE"],
  },
  {
    slug: "vqe-benchmarking-reproducibility",
    date: "2026-04-18",
    readingTime: "6 min read",
    title: "Why VQE Benchmarks Are So Hard to Reproduce — and How QEncode Fixes It",
    excerpt:
      "Most published VQE results can't be reproduced. The reasons are technical but fixable: underdocumented ansatz construction, hardware-specific transpilation, and no standard error metric. QEncode Suite v2 addresses all three.",
    tags: ["reproducibility", "VQE", "methodology", "certification"],
  },
];

function formatDate(iso) {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export default function BlogPage() {
  return (
    <main className="container max-w-3xl py-16">
      <div className="mb-12">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">Blog</h1>
        <p className="mt-3 text-muted-foreground">
          Technical articles on quantum algorithm benchmarking, VQE methodology, and reproducible
          quantum chemistry evaluation.
        </p>
      </div>

      <div className="space-y-10">
        {posts.map((post) => (
          <article key={post.slug} className="group border-b pb-10 last:border-0">
            <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
              <time dateTime={post.date}>{formatDate(post.date)}</time>
              <span>·</span>
              <span>{post.readingTime}</span>
            </div>
            <h2 className="text-xl font-semibold text-foreground group-hover:text-primary transition-colors mb-2">
              <Link href={`/blog/${post.slug}`}>{post.title}</Link>
            </h2>
            <p className="text-muted-foreground text-sm leading-relaxed mb-4">{post.excerpt}</p>
            <div className="flex items-center justify-between">
              <div className="flex gap-2 flex-wrap">
                {post.tags.map((tag) => (
                  <span
                    key={tag}
                    className="inline-flex items-center rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <Link
                href={`/blog/${post.slug}`}
                className="text-sm font-medium text-primary hover:underline shrink-0"
              >
                Read →
              </Link>
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
