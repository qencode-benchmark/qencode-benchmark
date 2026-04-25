# Changelog

All notable changes to QEncode are recorded here.

---

## 2026-04-25 — Phase 5: Customer Dashboard + Auth

- Added Clerk v6 authentication to the website
- Customer dashboard at `/dashboard` showing live order status (queued → running → completed)
- Sign-in page at `/sign-in` with QEncode branding
- Navbar updated: signed-out users see Sign In + Apply; signed-in users see Dashboard + Certify
- Customer confirmation email now includes "View order status →" button linking to dashboard
- Fixed Next.js 15 async `params` in `/api/admin/jobs/[id]` route

## 2026-04-25 — Blog + SEO

- Added `/blog` with two technical posts:
  - *UCCSD vs Hardware-Efficient Ansatz: What the Benchmark Data Actually Shows*
  - *Why VQE Benchmarks Are So Hard to Reproduce — and How QEncode Fixes It*
- Blog added to Navbar and footer
- Sitemap updated with blog post URLs and per-route priority/frequency tuning
- Website submitted to Google Search Console

## 2026-04-25 — Phase 4: Automated Job Queue (Ubuntu Poller)

- `scripts/job_poller.py` — daemon polls `/api/admin/jobs` every 60 s
- Installs as a systemd service (`qencode-poller.service`), auto-starts on boot, restarts on crash
- End-to-end automation: payment → DB order → poller claims job → runs benchmark → publishes leaderboard → marks job complete
- REST API: `GET /api/admin/jobs`, `POST /api/admin/jobs?action=claim`, `POST /api/admin/jobs/:id`
- Auth: `Authorization: Bearer <LEADERBOARD_PUBLISH_SECRET>` on all admin endpoints

## 2026-04-22 — Phase 3: Apply Form Backend

- `/apply` form wired to real API route (`POST /api/apply`)
- Validates required fields, derives plan recommendation (Starter / Team / Enterprise)
- Sends formatted confirmation email to applicant and admin notification via Resend
- Replaced mailto: link with proper async form with idle/submitting/success/error states

## 2026-04-20 — Phase 2: Dynamic Leaderboard (Neon Postgres)

- Leaderboard now reads from Neon Postgres at runtime instead of static CSV at build time
- `lib/db.js` — schema (`leaderboard_entries`, `leaderboard_metadata`, `orders`), idempotent `ensureSchema()`
- `POST /api/admin/publish-leaderboard` — replaces all leaderboard entries and busts cache via `revalidatePath`
- `scripts/publish_leaderboard_live.py` — reads CSVs, pushes to live API with Bearer auth
- `/leaderboard` set to `force-dynamic` to prevent build-time prerender failures
- CSV fallback when DB is empty (local dev)

## 2026-04-18 — Phase 1: Payment Webhook + Automated Emails

- Lemon Squeezy webhook at `POST /api/webhooks/lemonsqueezy`
- HMAC-SHA256 signature verification with `timingSafeEqual`
- Sends customer confirmation email and admin notification via Resend on `order_created` (paid)
- `/certify/success` page updated to show 3-step timeline instead of mailto button
- `lib/email.js` — `sendCustomerConfirmation`, `sendAdminNotification`, `sendApplyConfirmation`, `sendApplyAdminNotification`

## 2026-04-10 — Suite v2 Launch

- QEncode Standard Suite v2 published: H₂, LiH, HF, N₂, BeH₂ at JW/parity/BK encodings
- UCCSD and HEA ansatz families, FCI reference energies via PySCF
- Three leaderboard categories: accuracy, cost, balanced score
- Ed25519-signed certification receipts
- Next.js website launched at qencode-benchmark.org on Vercel
