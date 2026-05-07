export default function robots() {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/"
      }
    ],
    sitemap: "https://www.qencode-benchmark.org/sitemap.xml",
    host: "https://www.qencode-benchmark.org"
  };
}
