# Release Notes

See [CHANGELOG.md](CHANGELOG.md) for full version history.

---

## Suite v3.1 — 6-31G Basis Release

**42 benchmark entries · 30 certified · 12 research · 7 molecules**

### What changed from Suite v3 (STO-3G)

Suite v3.1 upgrades the basis set from STO-3G to **6-31G (split-valence)**, the standard for
NISQ-era VQE demonstrations in the literature. The 6-31G basis produces CCSD(T) correlation
energies approximately 5× larger than STO-3G, making the classical comparison physically
meaningful.

All benchmark definitions (molecules, active spaces, mappings, ansatz families, optimizer
protocol) are identical to Suite v3. Only the basis set changed.

### Certification criterion

All 30 certified entries satisfy `beats_ccsd_t = True`:

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

The VQE simulation error is smaller than the CCSD(T) correlation energy — the best
single-reference perturbative classical result for that molecule and basis. This is a
precision comparison within the same molecular system, not a claim that quantum computing
beats classical computing overall.

### Research entries (12)

N₂ entries are validated but do not meet the 0.01 Ha certification threshold. N₂ has a
strongly-correlated triple bond and 404 UCCSD variational parameters under 6-31G. Results
are correct — the gap reflects the method's limitation on this system.

### Downloads

- GitHub Release: https://github.com/qencode-benchmark/qencode-benchmark/releases/tag/v3.1.0
- Artifact ZIP: `qencode-suite-v3.1-artifacts.zip` — 42 JSON entries, leaderboard CSVs, schema

### Live leaderboard

https://www.qencode-benchmark.org/leaderboard
