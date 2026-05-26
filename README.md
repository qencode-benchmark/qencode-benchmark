# QEncode — Quantum Algorithm Benchmarking Standard

**QEncode is the open benchmark standard for reproducible VQE quantum chemistry evaluation — free to run, certified when you need signed results.**

🌐 **[qencode-benchmark.org](https://www.qencode-benchmark.org)** &nbsp;·&nbsp; 📊 **[Live Leaderboard](https://www.qencode-benchmark.org/leaderboard)** &nbsp;·&nbsp; 📄 **[Benchmark Spec](https://www.qencode-benchmark.org/benchmark)** &nbsp;·&nbsp; 📝 **[Blog](https://www.qencode-benchmark.org/blog)**

[![Reproducibility CI](https://github.com/qencode-benchmark/qencode-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/qencode-benchmark/qencode-benchmark/actions/workflows/ci.yml)

---

## What QEncode does

Most published VQE results cannot be independently reproduced — different teams use different molecules, basis sets, encodings, active spaces, and error metrics, making cross-study comparison unreliable. QEncode fixes this with:

- **Fixed benchmark definitions** — 10 molecules, cc-pVDZ basis, chemistry-driven active spaces, 3 qubit encodings, 2 ansatz families, CASCI reference energies
- **Open-source pipeline** — one script (`generate_entry_v4.py`) with a pinned environment (`requirements-v4.txt`). Any result is independently reproducible
- **Signed certification** — entries are signed with Ed25519 and carry a SHA-256 provenance hash
- **Public leaderboard** — certified entries ranked by accuracy gap, circuit cost, and balanced score
- **DARPA QB-GSEE aligned** — N₂ certified at cc-pVDZ, directly comparable to QB-GSEE target specification

---

## Suite v4 — Current (cc-pVDZ basis)

### Certified molecules — 7 molecules, 26 certified entries

| Molecule | Formula | Active Space | JW Qubits | Tapered | Certified Entries | Notes |
|---|---|---|---|---|---|---|
| H₂ | Hydrogen | [2e, 2o] | 4 | 1 | 6 | JW + PAR + BK |
| HF | Hydrogen Fluoride | [2e, 2o] | 4 | 1 | 6 | JW + PAR + BK |
| LiH | Lithium Hydride | [4e, 4o] | 8 | 5 | 3 | JW + PAR only |
| BeH₂ | Beryllium Hydride | [4e, 4o] | 8 | — | 4 | D∞h, PAR/UCCSD works |
| H₂O | Water | [4e, 4o] | 8 | — | 3 | JW + PAR only |
| NH₃ | Ammonia | [4e, 4o] | 8 | — | 3 | JW + PAR only |
| N₂ | Nitrogen | [6e, 6o] | 12 | 8 | 1 | **CASSCF required**, 2.0 mHa gap |

### Upcoming targets — v4.1 / v4.2

| Molecule | Formula | Active Space | JW Qubits | Notes |
|---|---|---|---|---|
| H₂CO | Formaldehyde | [4e, 4o] | 8 | New in v4.1 |
| C₄H₆ | 1,3-Butadiene | [4e, 4o] | 8 | First conjugated molecule, v4.1 |
| Benzene | C₆H₆ | [6e, 6o] | 12 | **CASSCF required**, first aromatic, v4.2 |

**Encoding notes:**
- BK excluded for all molecules except H₂ and HF (PennyLane 0.45 imaginary artefacts in tapering for active spaces > [2,2])
- PAR/UCCSD excluded for LiH, H₂O, NH₃, N₂, benzene (JW-basis UCCSD operators incompatible with Parity tapering)
- CASSCF orbital optimization required for N₂ and benzene (HF orbitals cannot cleanly partition the active space)

---

## Quick start

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
pip install -r requirements-v4.txt

# Run a single entry (H₂, Jordan-Wigner, UCCSD)
python scripts/generate_entry_v4.py \
  --molecule H2 --mapping jordan_wigner \
  --ansatz-type uccsd --out-dir releases/v4/db

# N₂ requires CASSCF orbital optimization
python scripts/generate_entry_v4.py \
  --molecule N2 --mapping jordan_wigner \
  --ansatz-type uccsd --orbital-opt casscf \
  --multistart 1 --max-iter 10000 \
  --out-dir releases/v4/db

# Benzene (first aromatic — v4.2 target)
python scripts/generate_entry_v4.py \
  --molecule benzene --mapping jordan_wigner \
  --ansatz-type uccsd --orbital-opt casscf \
  --multistart 1 --max-iter 15000 \
  --backend lightning.qubit --out-dir releases/v4/db

# Verify any entry
python scripts/verify_entry.py releases/v4/db/<entry_id>.json

# Export leaderboard CSVs from db entries
python scripts/export_leaderboard_v4.py

# Publish to live leaderboard (requires LEADERBOARD_PUBLISH_SECRET)
python scripts/publish_leaderboard.py --secret $LEADERBOARD_PUBLISH_SECRET
```

> **Windows:** Use WSL2 + Conda. PySCF does not install natively on Windows.  
> **Long runs:** Use `nohup ... &` in a tmux session. `systemd-inhibit` does not work in WSL2.  
> **GPU:** Pass `--backend lightning.gpu` for lightning.gpu acceleration (requires cuQuantum).

---

## Pipeline

```
PySCF: HF → [CASSCF] → CASCI reference energy
         ↓
PennyLane: molecular Hamiltonian (JW / PAR / BK mapping)
         ↓
Z2 symmetry tapering (reduces qubit count)
         ↓
COBYLA VQE (UCCSD or HEA ansatz)
         ↓
SHA-256 provenance hash + Ed25519 signature → JSON entry
```

All reference energies (HF, MP2, CCSD, CCSD(T), CASCI) are computed by PySCF. The VQE gap is always `|E_VQE − E_CASCI|` — never against full-system FCI or a classical approximation.

---

## Leaderboard categories

| Category | Ranked by |
|---|---|
| **Accuracy** | Lowest `\|E_VQE − E_CASCI\|` gap (Ha) |
| **Lowest Cost** | Fewest 2-qubit gates, then circuit depth |
| **Balanced** | Equal-weight normalised rank score |
| **Research** | Validated entries (gap ≥ 0.01 Ha) — recorded, never discarded |

---

## Repository structure

```
qencode-db/
├── molecules_v4.json           # Suite v4 molecule catalog
├── requirements-v4.txt         # Pinned environment (PySCF 2.5.0, PL 0.45)
├── requirements-v3.txt         # Frozen v3 environment
├── scripts/
│   ├── generate_entry_v4.py    # Main pipeline (PySCF → PL → taper → VQE → JSON)
│   ├── export_leaderboard_v4.py # JSON db → CSVs with deduplication
│   ├── publish_leaderboard.py  # CSVs → Neon Postgres via /api/admin/publish-leaderboard
│   ├── verify_entry.py         # Re-run any entry, auto-detects v3 vs v4 schema
│   └── of_bridge.py            # OpenFermion Parity-mapping bridge
├── releases/
│   ├── v4/db/                  # Suite v4 (cc-pVDZ) entry JSONs ← current
│   ├── v3.1/db/                # Suite v3.1 (6-31G) frozen entries
│   └── v3/db/                  # Suite v3 (STO-3G) frozen entries
├── docs/
│   ├── QUICK_START.md          # Running your first v4 entry
│   ├── BENCHMARK_SPEC_V4.md    # Full v4 specification
│   └── LEADERBOARD_RULES_V1.md # Leaderboard eligibility and scoring rules
├── website/                    # Next.js 15 site on Vercel
│   ├── app/leaderboard/        # Live leaderboard page
│   ├── app/entry/[id]/         # Per-entry verification page
│   └── lib/                    # Neon DB access, data loading
└── schema/schema_v4.json       # Entry JSON schema (v4)
```

---

## Entry ID format (v4)

```
{mol}_{basis}_{MAP}_{ANS}_v4[_casscf]_tapered__sha256_{hash16}

Example: N2_ccpvdz_JW_UCCSD_v4_casscf_tapered__sha256_82e00cea5a20cd83
```

---

## Reproducibility and CI

The CI badge above runs on every commit. It re-generates H₂ and HF entries from scratch using the pinned environment and verifies the VQE gap matches the stored artifact. The v4 smoke job additionally checks that the gap is below the 0.01 Ha certification threshold.

To verify any entry locally:

```bash
python scripts/verify_entry.py releases/v4/db/N2_ccpvdz_JW_UCCSD_v4_casscf_tapered__sha256_82e00cea5a20cd83.json
```

---

## Certification

The benchmark suite is free to run yourself. Managed certification — with Ed25519-signed artifacts, CASCI reference verification, and an audit-ready report — is available for teams that need verified results for publications, grant applications, or hardware evaluations.

→ [qencode-benchmark.org/apply](https://www.qencode-benchmark.org/apply)  
→ [qencode-benchmark.org/pricing](https://www.qencode-benchmark.org/pricing)

---

## Citation

If you use QEncode in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff).

```
QEncode Benchmark Suite v4 (2026). qencode-benchmark.org
```

## Contact

support@qencode-benchmark.org
