# QEncode Leaderboard

The live leaderboard is at **[qencode-benchmark.org/leaderboard](https://www.qencode-benchmark.org/leaderboard)**.

This page is the short orientation. The authoritative documents are:

- [`TRUST_POLICY.md`](TRUST_POLICY.md) — what *certified* means (gap < 0.01 Ha), the two
  tiers, and what every other badge is
- [`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md) — how rows are ranked, eligibility
  per category, and the dated amendments

---

## Tiers

| Tier | Condition |
|---|---|
| **Certified** | `\|E_VQE − E_CASCI\| < 0.01 Ha` |
| **Research** | gap ≥ 0.01 Ha — recorded and published, never discarded |

## Categories

| Category | Eligible | Ranked by |
|---|---|---|
| **Accuracy** | certified | gap, ascending |
| **Lowest Cost** | certified, with transpiled circuit metrics | 2-qubit gates, then depth |
| **Balanced** | same as Lowest Cost | equal-weight blend of the two rankings, in rank space |
| **Research** | not certified | gap, ascending |

Rankings are global across the suite; molecule, mapping and ansatz filters narrow the view
without changing the ranks.

## Badges and markers — none of these is certification

| Shown | Means |
|---|---|
| **Certified** | gap < 0.01 Ha. The only thing that sets the tier. |
| **Beats CCSD(T)** | `\|E_VQE − E_CASCI\| < \|E_CCSD(T) − E_HF\|`: the VQE error is smaller than the CCSD(T) correlation energy for the same molecule and basis. A precision comparison within one system, not a claim that quantum beats classical. Informational badge; a certified entry can lack it. |
| **1.6 mHa line** | chemical accuracy (1 kcal/mol). Reported, not required. |
| **CASSCF** | orbitals were optimised before the active space was cut, used where HF orbitals do not partition cleanly. |
| **T-gate / non-Clifford count** | fault-tolerant resource estimate from the pre-transpilation circuit. |

## Entry pages

Every row links to `/entry/<entry_id>`: geometry, energies, circuit stats, optimiser
settings, exact tool versions, the SHA-256 provenance hash and its Ed25519 signature.

## Regenerating locally

```bash
python scripts/export_leaderboard_v4.py --dry-run     # entry JSONs -> CSVs, nothing written
python scripts/export_leaderboard_v4.py               # writes website/public/data/
```

## Current suite

Suite v4.4 — cc-pVDZ — 54 entries across 16 molecules, 47 certified, 7 research. The
frozen v3.1 suite (6-31G) is kept in `releases/v3.1/` and reproduces with
`requirements-v3.txt`; see [`RELEASE_NOTES.md`](RELEASE_NOTES.md).
