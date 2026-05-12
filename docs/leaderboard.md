# QEncode Leaderboard

The live leaderboard is at **[qencode-benchmark.org/leaderboard](https://www.qencode-benchmark.org/leaderboard)**.

---

## Categories

| Category | Ranked by |
|----------|-----------|
| **Accuracy** | Lowest `|E_VQE − E_CASCI|` gap (Ha) |
| **Lowest Cost** | Fewest 2-qubit gates, then circuit depth |
| **Balanced** | Equal-weight normalized rank score |
| **Research** | Validated entries (gap ≥ 0.01 Ha or research-tier molecules) |

---

## Certification badge

The **Beats CCSD(T)** badge means:

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

The VQE simulation error is smaller than the CCSD(T) correlation energy for that molecule
and basis set. This is a precision comparison within the same molecular system — not a
claim that quantum beats classical computing overall.

---

## Entry pages

Every leaderboard row links to `/entry/<entry_id>` showing full geometry, energies,
circuit stats, optimizer settings, tool versions, and the SHA-256 provenance hash.

---

## Regenerate leaderboard CSVs locally

```bash
python scripts/export_leaderboard_v3.py \
  --db-dir releases/v3.1/db \
  --suite-version 3.1
```

Outputs: `leaderboard_accuracy.csv`, `leaderboard_hardware_cost.csv`,
`leaderboard_balanced.csv`, `leaderboard_research.csv`, `leaderboard_metadata.json`.

---

## Current suite

Suite v3.1 — 6-31G basis — 30 certified + 12 research entries across 7 molecules.

See [RELEASE_NOTES.md](RELEASE_NOTES.md) for details.
