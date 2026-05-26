# Changelog

All notable changes to QEncode are recorded here.

---

## 2026-05-26 — Suite v4.2: Website Audit + SEO

- Homepage redesigned — free-first strategy, leaderboard as primary CTA, molecule catalog table replaces fake hardcoded data
- All stale Suite v2/v3 references removed from every page
- Navbar: Methodology added (was missing), GitHub button added, CTA renamed "Get Started"
- `/benchmark` rewritten with correct v4 qubit counts, full 10-molecule table, encoding exclusion notes
- `/methodology` updated to v4 pipeline (CASSCF, cc-pVDZ, accurate iteration counts)
- `/about` rewritten: real story, N₂ achievement, DARPA QB-GSEE alignment, principles
- `/docs` quick-start commands added, stale v2 doc links fixed
- `/apply` gatekeeping language removed, purpose clarified
- `/certify` Suite v2 → v4, apply-first flow added
- `/dashboard` placeholder replaced with useful quick-links grid
- Sitemap: N₂ blog post added (was missing), methodology priority raised
- robots.js: /api/ and post-conversion pages disallowed from indexing
- Article JSON-LD schema added to all 6 blog posts (rich results eligible)
- CITATION.cff created in repo root (was missing)
- README fully rewritten for v4

---

## 2026-05-21 — Suite v4.1: N₂ Certified + Benzene HEA

- N₂ JW/UCCSD certified: gap = 2.015 mHa, 12→8 qubits, 404 parameters, CASSCF orbital optimization
- N₂ JW/HEA and PAR/HEA validated (Research tab): gap = 0.121 Ha — HEA insufficient for triple bond
- Benzene JW/HEA validated: 12→9 qubits, 923 Pauli terms, 63 HEA params, gap = 0.091 Ha
- H₂CO and C₄H₆ added to molecules_v4.json as tier="target"
- `--orbital-opt casscf` flag: CASSCF pre-optimises orbital basis before VQE (required for N₂, benzene)
- `--reps` flag: HEA layer count control
- `--backend` flag: default.qubit | lightning.qubit | lightning.gpu
- VQE checkpoint: `.ckpt_*.json` written after every restart, auto-deleted on success
- VQE early-stop: fires when gap < 0.01 Ha, records actual restarts completed
- Export deduplication: keeps best gap per (molecule, mapping, ansatz, orbital_opt)
- Blog post: "Certifying N₂: QEncode Benchmarks the Triple Bond"
- Website: CASSCF badge (purple) on leaderboard rows; cc-pVDZ basis chip (blue)
- Leaderboard: 26 certified + 3 research entries

---

## 2026-05-14 — Suite v4.0: cc-pVDZ Foundation

- Upgraded basis from 6-31G to cc-pVDZ (publication-grade)
- `generate_entry_v4.py` and `schema_v4.json` — new v4 pipeline with PySCF 2.5.0 + PennyLane 0.45
- Fixed BK complex-taper bug (PL 0.45 resolves imaginary artefact for H₂ and HF)
- BK excluded for all molecules with active spaces > [2,2] (artefact too large to strip)
- PAR/UCCSD excluded for LiH, H₂O, NH₃ (JW-basis operator mismatch)
- 25 certified entries across 6 molecules at cc-pVDZ
- CI smoke-v4 job: re-generates H₂+HF, verifies gap < 0.01 Ha
- GitHub Release v4.0.0

---

## 2026-05-12 — Suite v3.1 Release (6-31G basis)

- Upgraded basis set from STO-3G to 6-31G (split-valence) — ~5× larger CCSD(T) correlation energies
- 42 benchmark entries: 30 certified + 12 research (N₂) across 7 molecules and 3 mappings
- All 30 certified entries satisfy `|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|`
- Per-entry verification pages live at `/entry/<entry_id>`
- GitHub Release v3.1.0 with `qencode-suite-v3.1-artifacts.zip` attached
- Badge renamed "Beats CCSD(T)" with clarifying tooltip
- UCCSD circuit metrics note added to entry pages explaining symbolic operators
- Ansatz Guide panel added to leaderboard (UCCSD vs HEA comparison)

---

## 2026-04-25 — Phase 5: Customer Dashboard + Auth

- Added Clerk v6 authentication to the website
- Customer dashboard at `/dashboard` showing live order status (queued → running → completed)
- Sign-in page at `/sign-in` with QEncode branding
- Navbar updated: signed-out users see Sign In + Apply; signed-in users see Dashboard + Certify
- Customer confirmation email now includes "View order status →" button linking to dashboard
- Fixed Next.js 15 async `params` in `/api/admin/jobs/[id]` route

## 2026-04-25 — Blog + SEO

- Added `/blog` with three technical posts:
  - *Jordan-Wigner vs Parity vs Bravyi-Kitaev: A Practical Comparison for VQE*
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
