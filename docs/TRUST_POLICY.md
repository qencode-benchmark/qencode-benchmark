# Trust Policy — QEncode Suite v3.1

## Certification criterion

A Suite v3.1 entry is **Certified** when:

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

In plain terms: the VQE simulation error (gap between VQE energy and the exact CASCI
ground state) must be smaller than the CCSD(T) correlation energy — the best
single-reference perturbative classical result for that molecule and basis set.

This is a precision comparison within the same molecular system. It is not a claim that
quantum computing beats classical computing overall.

All 30 certified Suite v3.1 entries satisfy this criterion.

---

## Research tier

Entries that do not meet the certification threshold are labelled **Validated (Research)**.
They are correct and reproducible — the gap reflects a physical limitation of the method
on that system (e.g. N₂'s strongly-correlated triple bond), not an implementation error.

Suite v3.1 has 12 research-tier entries, all from N₂ with the 6-31G basis.

---

## Provenance

Every entry includes:
- `entry_hash_sha256` — SHA-256 hash of the canonical entry JSON
- `provenance.tool_versions` — exact Python, PySCF, PennyLane, SciPy, NumPy versions
- `created_utc` — UTC timestamp of generation

The hash is reproducible: running `generate_entry_v3.py` with the same flags and seed
must produce a matching hash.
