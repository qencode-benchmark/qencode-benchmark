# QEncode — Quantum Algorithm Benchmarking Standard

**QEncode is the open benchmark standard for reproducible VQE quantum chemistry evaluation — free to run, certified when you need signed results.**

🌐 **[qencode-benchmark.org](https://www.qencode-benchmark.org)** &nbsp;·&nbsp; 📊 **[Live Leaderboard](https://www.qencode-benchmark.org/leaderboard)** &nbsp;·&nbsp; 📄 **[Benchmark Spec](https://www.qencode-benchmark.org/benchmark)** &nbsp;·&nbsp; 📝 **[Blog](https://www.qencode-benchmark.org/blog)**

[![Reproducibility CI](https://github.com/qencode-benchmark/qencode-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/qencode-benchmark/qencode-benchmark/actions/workflows/ci.yml)

---

## What QEncode does

Most published VQE results cannot be independently reproduced — different teams use different molecules, basis sets, encodings, active spaces, and error metrics, making cross-study comparison unreliable. QEncode fixes this with:

- **Fixed benchmark definitions** — 16 molecules, cc-pVDZ basis, chemistry-driven active spaces, 3 qubit encodings, 3 ansatz families, CASCI reference energies
- **Open-source pipeline** — one script (`generate_entry_v4.py`) with a pinned environment (`requirements-v4.txt`). Any result is independently reproducible
- **Enforced determinism** — the linear-algebra backend is pinned to a single thread before NumPy loads, because multi-threaded BLAS makes gradient-free VQE non-reproducible ([why](https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug))
- **Signed certification** — entries are signed with Ed25519 and carry a SHA-256 provenance hash
- **Public leaderboard** — certified entries ranked by accuracy gap, circuit cost, and balanced score
- **Fault-tolerant resource estimates** — every entry records non-Clifford and T-gate counts alongside its accuracy
- **DARPA QB-GSEE aligned** — N₂ certified at cc-pVDZ, directly comparable to QB-GSEE target specification

---

## Suite v4.4 — Current (cc-pVDZ basis)

**47 certified entries across 16 molecules** (54 entries total; 7 recorded as research tier).
An entry is *certified* when its gap to the active-space CASCI reference is below 10 mHartree.

| Molecule | Name | Active space | Qubits (JW → tapered) | Orbitals | Certified | Best gap (mHa) |
|---|---|---|---|---|---|---|
| H₂ | Hydrogen | [2e, 2o] | 4 → 1 | HF | 6 | &lt;0.001 (PAR/UCCSD) |
| HF | Hydrogen fluoride | [2e, 2o] | 4 → 1 | HF | 6 | &lt;0.001 (PAR/UCCSD) |
| LiH | Lithium hydride | [4e, 4o] | 8 → 5 | HF | 3 | 0.003 (JW/UCCSD) |
| BeH₂ | Beryllium hydride | [4e, 4o] | 8 → 3 | HF | 4 | &lt;0.001 (PAR/HEA) |
| H₂O | Water | [4e, 4o] | 8 → 4 | HF | 3 | &lt;0.001 (JW/UCCSD) |
| NH₃ | Ammonia | [4e, 4o] | 8 → 5 | HF | 3 | 0.032 (JW/UCCSD) |
| H₂CO | Formaldehyde | [4e, 4o] | 8 → 4 | HF | 1 | 1.124 (JW/ADAPT) |
| C₄H₆ | 1,3-Butadiene | [4e, 4o] | 8 → 4 | HF | 1 | 2.829 (JW/ADAPT) |
| (H₂O)₂ | Water dimer | [4e, 4o] | 8 → 5 | HF | 4 | 0.002 (JW/UCCSD) |
| H₄ | Hydrogen chain | [4e, 4o] | 8 → 5 | HF | 4 | 2.222 (JW/UCCSD) |
| C₄H₄ | Cyclobutadiene | [4e, 4o] | 8 → 6 | CASSCF | 4 | 5.963 (JW/ADAPT) |
| N₂ | Nitrogen | [6e, 6o] | 12 → 8 | CASSCF | 3 | 4.513 (JW/HEA) |
| H₆ | Hydrogen chain | [6e, 6o] | 12 → 9 | CASSCF | 1 | 9.273 (JW/ADAPT) |
| C₆H₆ | Benzene | [6e, 6o] | 12 → 9 | CASSCF | 2 | 8.741 (JW/HEA) |
| H₈ | Hydrogen chain | [8e, 8o] | 16 → 13 | CASSCF | 1 | 9.797 (JW/ADAPT) |
| H₁₀ | Hydrogen chain | [10e, 10o] | 20 → 18 | CASSCF | 1 | 9.977 (JW/ADAPT) |

**Encoding notes:**
- BK excluded for all molecules except H₂ and HF (PennyLane imaginary artefacts in tapering for active spaces > [2,2])
- PAR/UCCSD excluded for several molecules (JW-basis UCCSD operators incompatible with Parity tapering)
- CASSCF orbital optimization is used where HF orbitals cannot cleanly partition the active space (N₂, H₆, C₄H₄, benzene, H₈, H₁₀)
- H₈ and H₁₀ are the largest certified systems (16 and 20 qubits before tapering), reached with ADAPT-VQE and a sparse statevector engine

---

## Quick start

**Docker (recommended — pinned environment, determinism already enforced):**

```bash
docker build -t qencode .
docker run --rm -v "$PWD/out:/work/out" qencode \
  --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir /work/out
```

**Local install:**

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
pip install -r requirements-v4.txt      # Python 3.11

# Run a single entry (H₂, Jordan-Wigner, UCCSD) — takes about a minute
python scripts/generate_entry_v4.py \
  --molecule H2 --mapping jordan_wigner \
  --ansatz-type uccsd --out-dir releases/v4/db

# Verify any published entry reproduces
python scripts/verify_entry.py releases/v4/db/<entry_id>.json

# Check whether YOUR environment can produce reproducible VQE results
python tools/check_vqe_reproducibility.py
```

See **[QUICKSTART.md](QUICKSTART.md)** for a five-minute walkthrough, including how to compare your own result against the leaderboard.

More examples:

```bash
# N₂ requires CASSCF orbital optimization
python scripts/generate_entry_v4.py \
  --molecule N2 --mapping jordan_wigner --ansatz-type uccsd \
  --orbital-opt casscf --multistart 1 --max-iter 10000 --out-dir releases/v4/db

# ADAPT-VQE — the only method that certifies the large chains
python scripts/generate_entry_v4.py \
  --molecule H8 --mapping jordan_wigner --ansatz-type adapt \
  --orbital-opt casscf --adapt-engine statevector --adapt-inner bfgs \
  --adapt-max-ops 300 --out-dir releases/v4/db

# Export leaderboard CSVs from db entries
python scripts/export_leaderboard_v4.py
```

> **Windows:** Use WSL2 or Docker. PySCF does not install natively on Windows.
> **Long runs:** Use `nohup ... &` in a tmux session. `systemd-inhibit` does not work in WSL2.
> **GPU:** Pass `--backend lightning.gpu` for acceleration (requires cuQuantum).

---

## Reproducibility

Reproducibility is enforced by the pipeline, not assumed. Before any entry is written, a guard checks that:

1. the linear-algebra backend is restricted to **one thread**,
2. installed package versions match `requirements-v4.txt`, and
3. the git tree is clean, so the recorded commit describes the code that ran.

An entry that fails any check is not written. Each entry records its thread count and full software environment in its provenance block.

The single-thread requirement is not a detail. Multi-threaded BLAS sums floating-point numbers in whatever order cores finish, which perturbs an energy in its last bits — and a gradient-free optimizer such as COBYLA, which picks its next step by *comparing* energies, can be driven into a different local minimum by that noise. We found this in our own published numbers and re-ran the entire suite. The full account is in **[We Audited Our Own VQE Benchmark](https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug)**.

To check your own setup — not just ours:

```bash
python tools/check_vqe_reproducibility.py            # scorecard for this machine
python tools/check_vqe_reproducibility.py --record   # write a provenance receipt
```

---

## Pipeline

```
PySCF: HF → [CASSCF] → CASCI reference energy
         ↓
Qubit Hamiltonian from active-space integrals (OpenFermion bridge)
         ↓  JW / PAR / BK mapping
Z2 symmetry tapering (reduces qubit count)
         ↓
VQE — UCCSD, HEA, or ADAPT-VQE
      COBYLA (gradient-free) or L-BFGS-B (analytic gradients)
      single-threaded BLAS, pinned before NumPy loads
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

Cost and Balanced also report an estimated **T-gate count**, the resource-relevant cost of a fault-tolerant implementation.

---

## Repository structure

```
qencode-db/
├── molecules_v4.json           # Suite v4 molecule catalog
├── requirements-v4.txt         # Pinned environment (PySCF 2.6.2, PennyLane 0.45.0)
├── requirements-v3.txt         # Frozen v3 environment
├── requirements-tools.txt      # Extra deps for the leaderboard scripts (pandas, cryptography)
├── Dockerfile                  # Pinned, single-threaded run environment
├── QUICKSTART.md               # Five-minute walkthrough
├── scripts/
│   ├── generate_entry_v4.py    # Main pipeline (PySCF → taper → VQE → JSON)
│   ├── export_leaderboard_v4.py # JSON db → CSVs with deduplication
│   ├── publish_leaderboard.py  # CSVs → Neon Postgres via /api/admin/publish-leaderboard
│   ├── verify_entry.py         # Re-run any entry, auto-detects v3 vs v4 schema
│   └── of_bridge.py            # OpenFermion integral → qubit Hamiltonian bridge
├── tools/
│   └── check_vqe_reproducibility.py  # Reproducibility scorecard for any VQE setup
├── releases/
│   ├── v4/db/                  # Suite v4 (cc-pVDZ) entry JSONs ← current
│   ├── v3.1/db/                # Suite v3.1 (6-31G) frozen entries
│   └── v3/db/                  # Suite v3 (STO-3G) frozen entries
├── docs/
│   ├── GETTING_STARTED.md      # Longer-form introduction
│   ├── SUBMISSIONS.md          # Submitting a result
│   ├── LEADERBOARD_RULES_V2.md # How rows are ranked
│   ├── TRUST_POLICY.md         # Certified vs research tier
│   └── V4_PLAN.md              # Suite roadmap
├── website/                    # Next.js site on Vercel
└── schema/schema_v4.json       # Entry JSON schema (v4)
```

---

## Entry ID format (v4)

```
{mol}_{basis}_{MAP}_{ANS}_v4[_casscf]_tapered__sha256_{hash16}

Example: N2_ccpvdz_JW_ADAPT_v4_casscf_tapered__sha256_850d9d253b878943
```

---

## Reproducibility and CI

The CI badge above runs on every commit. It re-generates H₂ and HF entries from scratch using the pinned environment and verifies the VQE gap matches the stored artifact. The v4 smoke job additionally checks that the gap is below the 0.01 Ha certification threshold.

---

## Certification

The benchmark suite is free to run yourself. Managed certification — with Ed25519-signed artifacts, CASCI reference verification, and an audit-ready report — is available for teams that need verified results for publications, grant applications, or hardware evaluations.

→ [qencode-benchmark.org/apply](https://www.qencode-benchmark.org/apply)

---

## Citation

If you use QEncode in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff).

```
QEncode Benchmark Suite v4 (2026). qencode-benchmark.org
```

## Contributing

Contributions are welcome — especially a result of ours that does not reproduce for
you. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, the determinism rules the
project enforces, and how to propose a molecule or submit an entry.

---

## License

Apache License 2.0 — see [LICENSE](LICENSE). Free to use, modify, and redistribute,
including commercially, with an express patent grant.

---

## Contact

support@qencode-benchmark.org
