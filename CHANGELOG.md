# Changelog

All notable changes to QEncode are recorded here.

> **Consolidated 2026-09-04.** There were two changelogs — this file and
> `docs/CHANGELOG.md` — with *different* histories: this one held the dated product and
> suite releases from April and May, the other held version-tagged suite entries going
> back to v1.0.0. Neither was complete. They are merged here and `docs/CHANGELOG.md` is
> now a pointer.
>
> **Suite v4.3 and v4.4 were never written up.** Rather than reconstruct them after the
> fact, the gap is stated: v4.3 added ADAPT-VQE and gradient-based optimisers, v4.4 added
> the sparse statevector engine that reached H₈ and H₁₀ and re-baselined the suite after
> the threading fix. Both are recorded in [`docs/V4_PLAN.md`](docs/V4_PLAN.md), the dated
> amendments in [`docs/LEADERBOARD_RULES_V2.md`](docs/LEADERBOARD_RULES_V2.md), and the
> git history.

---

## Unreleased — 2026-09-09 — reproduction is machine-bound, and the noisy tier completes

- **An entry reproduces bit-for-bit only on the machine that generated it.** The whole
  suite was re-verified on a second machine with the same pinned stack, the same seeds and
  one BLAS thread on both: 54 entries on an Intel Xeon 4316 cluster node and 41 on an AMD
  Threadripper workstation. Every entry reproduced exactly on its own machine and moved on
  the other, by between 10⁻¹⁶ and 8 × 10⁻³ Ha. Certification survives on **38 of the 40
  certified entries measured on a second machine**; seven were measured on one machine only
  and are reported as unmeasured, not as survivors. Two entries lose certification off their
  home machine (C₄H₄ and N₂ parity, hardware-efficient) and two more pass only because the
  movement happened to shrink the gap. The leaderboard now shows robustness as a measurement
  on 40 entries instead of a prediction on 5. `docs/CROSS_MACHINE.md`,
  `experiments/cross_machine/`, `scripts/verification_sweep.py`.
- **The cause is the BLAS kernel, and it was located rather than guessed.** OpenBLAS picks
  kernels by processor at run time. Forcing both machines onto the same kernel makes PySCF
  bit-identical across machines — Hamiltonian, Hartree–Fock and CASCI alike, CASSCF
  included — which retires the "CASSCF converged differently on another day" explanation
  that `docs/NOISY_TIER.md`, `docs/SECTOR_FIX.md` and the reference table had carried. The
  variational half is not deterministic even then: from an identical Hamiltonian and an
  energy function returning identical bits, the two machines' COBYLA runs still part ways.
  A probe of the two C libraries finds only `expm1` differing. Which residue moves the
  optimiser is not isolated, and the documents say so.
- **The optimiser rule is corrected.** A run amplifies if *any* comparison it makes steers
  control flow — the optimiser step or a multistart loop's stopping test — not only if the
  optimiser is gradient-free. An L-BFGS-B entry lost certification across machines because
  its multistart loop stops at the first attempt that certifies.
- **Entries record the machine they ran on**: processor, vector instruction sets, the BLAS
  kernel selected at run time, C library and operating system, in
  `provenance.environment.machine`. It is recorded and **not hashed** — hashing it would
  mean a regeneration on another machine changed the entry's hash even when every number
  was identical, which is the comparison the hash exists to support. All 54 published
  entries predate the field and their hashes are unchanged.
- **The noisy tier is complete: all 52 entries at or below 10 tapered qubits are measured.**
  The last two, the C₄H₄ Jordan–Wigner UCCSD and ADAPT entries, could not be rebuilt on the
  workstation at all: under its kernel the pipeline finds a third Z₂ symmetry and tapers
  cyclobutadiene to five qubits where the generating run found two and stored six. Run on
  the machine whose kernel matches the stored gauge, the re-derived Hamiltonian matches the
  stored coefficients exactly and both entries measure. The kernel can therefore change the
  qubit count, not only the last bit.
- **Two test faults found and fixed.** The saturated zero-noise-extrapolation check assumed
  that ε ≈ 1 means the state is already maximally mixed; ε counts *at least one*
  depolarizing event, and one event leaves the other wires correlated. And the reference H₂
  hash pin, once the fingerprint stopped being hashed, now asserts something stronger than
  before: two machines differing in processor, instruction sets and C library produce that
  entry identically, because H₂ converges rather than stopping on a comparison.

## Unreleased — 2026-09-07 — Z₂ sector fault fixed, 18 entries regenerated

- **Every non-Jordan–Wigner entry was tapered into the wrong symmetry sector.**
  `pennylane.qchem.optimal_sector` hard-codes the Jordan–Wigner Hartree–Fock occupation
  string and matches generator support against an unordered set of wires; both are wrong
  for parity and Bravyi–Kitaev, and the two bugs cancelled for exactly one configuration
  (NH₃ under Bravyi–Kitaev), which is why it looked fine there. The tapered ground state
  sat 0.30–0.76 Ha above CASCI and the difference was added back as a "constant
  correction", hiding it. `qchem.taper_hf` has the same assumption, so five further
  entries had the right sector but a Hartree–Fock reference built with the wrong encoding.
- **Fixed** in `_find_optimal_sector`, which now derives the sector from the mapping's own
  Hartree–Fock state, matches support by wire label, verifies the result against CASCI,
  and raises if nothing reproduces it. The constant-correction branch raises instead of
  shifting. New `_tapered_hf_state` and `_diagonal_energy` verify the reference state
  against the untapered Hartree–Fock energy.
- **18 entries regenerated**; none changed trust level; superseded files kept in
  `releases/v4/db_superseded/`. No Jordan–Wigner entry affected — 36 entries, including
  both hydrogen chains and every ADAPT result, are untouched.
- Fifteen new tests parametrised over all three mappings; `docs/SECTOR_FIX.md`;
  `tools/compare_regenerated.py` and `tools/apply_regenerated.py`.

## Unreleased — 2026-09-04 — the hardware-penalty track

- **Every entry at or below 10 tapered qubits now carries a measured hardware penalty**:
  the same circuit, same parameters, re-evaluated as a density matrix with a named
  gate-noise model's channels after every gate. Reported on the leaderboard as the
  *Noise* column, with the gap under noise and a Richardson zero-noise extrapolation on
  hover. A measurement track, not a certification criterion; no entry's tier, rank or
  hash changes. `tools/noisy_tier.py`, `experiments/noisy_tier/`, `docs/NOISY_TIER.md`.
- **Corrected the depolarizing convention** in `docs/GATE_NOISE.md` and
  `tools/predict_gate_noise_bias.py`: PennyLane's channel fully depolarizes with
  probability 4p/3, not p, so the earlier ε was understated by 4/3 per channel, and the
  "upper bound" there was an estimate. The rigorous bound ε·(λ_max − E) is now recorded
  and checked per entry.
- **Two findings recorded, not hidden.** (1) Every parity- and Bravyi-Kitaev-mapped
  entry (13 of 54) carries a "constant correction" of 0.3–0.76 Ha because the tapering
  selects a symmetry sector that does not contain the ground state; for the four
  one-qubit H₂/HF parity entries the tapered Hamiltonian is a single constant term, so
  their gap of exactly zero is vacuous. (2) CASSCF entries cannot have their stored
  circuits rebuilt from a re-derived Hamiltonian, because the converged active orbitals
  are fixed only by rounding; the tool rebuilds from the entry's own serialised terms.
  Both are documented in `docs/NOISY_TIER.md`; neither entry set has been modified.
- `tests/test_noisy_tier.py` (conventions, extrapolation, exponential splitting, and the
  internal consistency of every committed record).

## v4.5.0 — 2026-09-04 — first PyPI release

**The package version now moves independently of the suite version.** Suite v4.4 (the
data — molecules, basis, active spaces) is frozen until the paper it underpins is
published. The software is not frozen, so the two numbers part company here.

### Score a VQE result without running the pipeline

- `qencode.score(energy, molecule=..., optimizer=..., ansatz=...)` reports the gap to the
  exact ground state of the same active space, which of the two thresholds it clears, the
  certification margin, whether the (optimiser, ansatz) pair makes that margin fragile
  across machines, and where the number ranks among the published entries.
- The references for all 16 suite molecules ship inside the package as a 23 KB table, so
  **scoring imports no chemistry stack** — verified against the built wheel installed with
  no dependencies at all.
- It refuses rather than guesses: a mismatched active space raises, an energy below the
  variational minimum is reported before any gap, and nothing is ever called *certified*.
- `notebooks/score_your_vqe_result.ipynb` is the walkthrough, with executed outputs.

### Packaging

- Published to PyPI via **Trusted Publishing (OIDC)** — no API token exists anywhere.
- `.github/workflows/publish.yml` builds and `twine check --strict`s on every packaging
  change, and re-verifies zero-dependency scoring against the built wheel.

### Correctness and hygiene

- **Statevector ADAPT engine now verifies `B³ = -B` for every pool operator.** Fed a
  `taper_operation` pool its closed-form exponential is not exact and it reported energies
  *below* the exact ground state; it now raises. No published entry was affected — the two
  entries using this engine (H₈, H₁₀) use the generator pool, which is filtered on exactly
  this identity.
- One definition of *certified* across the repository, pinned by a test.
- Leaderboard shows certification margin, optimiser family, chemical accuracy and measured
  cross-environment robustness per row.
- The publish path verifies TLS and no longer forwards credentials across redirects.
- `scripts/` reduced from 63 files to 17; v1/v2 tooling moved to `scripts/legacy/`.
- Test suite runs in CI for the first time: 116 tests.

---

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

---

## v2.0.x (legacy)

### Overview
v2 database format and full, reproducible supply-chain verification pipeline: indexes, reporting, auditing, trusted exports, manifest + per-entry content hashes.

### Highlights
- v2 schema + v2 DB artifacts; migration from v1 → v2.
- Environment stamping; trusted set export; supply-chain integrity (manifest, entry_content_hashes, verification).
- Makefile pipeline: `make check`, `make release-local`, etc.

See [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md) for details.

---

## v2.0.0-alpha

### Highlights
- Introduced schema v2 (`schema/schema_v2.json`).
- Added v1 → v2 migration tooling.
- Added v2-specific tooling: v2 schema validator, index builder, benchmarks reporter (with `trusted` + flags), v2 audit script.
- Added provenance stamping into v2 entries (environment fingerprint).
- Added “trusted” export pipeline to produce a strict benchmark subset.

### Trusted benchmark set (v2)
A v2 entry is considered **trusted** when it satisfies the trust policy (see [docs/TRUST_POLICY.md](docs/TRUST_POLICY.md) (renamed from TRUSTED_POLICY.md)). The trusted export produces:
- `releases/v2/trusted/` JSON entries (trusted subset)
- `releases/v2/trusted/trusted_index.json`
- `releases/v2/trusted/trusted_benchmarks.csv`

### Supply-chain artifacts (v2)
- `releases/v2/db/manifest.json` — snapshot manifest with hashes over files under `releases/v2/db`.
- `releases/v2/db/entry_content_hashes.json` — canonical content hashes per v2 entry, with verification tooling.

---

## v1.0.0

### Highlights
- Validated all v1 entries against the v1 schema (`schema_v1.json`).
- Rebuilt `releases/v1/db/index.json` and `releases/v1/db/benchmarks.csv`.
- Added auditing checks to flag missing fields, legacy fields, and large VQE-vs-exact gaps.
- Canonicalization policy applied where appropriate.

### What’s included
- `releases/v1/db/` entries (JSON)
- `releases/v1/db/index.json`
- `releases/v1/db/benchmarks.csv`
- Tooling: schema validator, index builder, benchmarks report, audit script
