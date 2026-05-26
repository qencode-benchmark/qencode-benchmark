export default function robots() {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: [
          "/api/",
          "/certify/success",
          "/certify/cancel",
          "/dashboard",
          "/sign-in",
          "/verify/",
        ],
      },
    ],
    sitemap: "https://www.qencode-benchmark.org/sitemap.xml",
    host: "https://www.qencode-benchmark.org",
  };
}
