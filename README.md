# QEncode — Quantum Algorithm Benchmarking Standard

**QEncode is the standard for reproducible VQE evaluation, managed benchmark execution, and signed certification of quantum chemistry algorithms.**

🌐 **[qencode-benchmark.org](https://www.qencode-benchmark.org)** &nbsp;·&nbsp; 📊 **[Live Leaderboard](https://www.qencode-benchmark.org/leaderboard)** &nbsp;·&nbsp; 📄 **[Benchmark Spec](https://www.qencode-benchmark.org/benchmark)** &nbsp;·&nbsp; 💰 **[Pricing](https://www.qencode-benchmark.org/pricing)**

---

## What QEncode does

Most published VQE results cannot be independently reproduced — different teams use different molecules, encodings, error metrics, and hardware. QEncode fixes this with:

- **Fixed benchmark definitions** — 7 molecules, 3 qubit encodings, 2 ansatz families, exact CASCI reference energies
- **Managed execution** — benchmarks run on verified, reproducible infrastructure under identical conditions
- **Signed certification** — results are signed with Ed25519, producing a verifiable certification receipt
- **Public leaderboard** — certified entries appear on the live leaderboard, ranked by accuracy gap, circuit cost, and a balanced score
- **Per-entry artifact pages** — every leaderboard row links to `/entry/<id>` showing full geometry, energies, optimizer settings, tool versions, and a SHA-256 provenance hash

## Suite v3.1 benchmark molecules (6-31G basis)

| Molecule | Formula | Active Space | Qubits (JW, tapered) | Tier |
|----------|---------|-------------|---------------------|------|
| Hydrogen | H₂ | [2e, 2o] | 1 | Certified |
| Hydrogen Fluoride | HF | [2e, 2o] | 1 | Certified |
| Lithium Hydride | LiH | [4e, 4o] | 4 | Certified |
| Beryllium Hydride | BeH₂ | [4e, 4o] | 3 | Certified |
| Water | H₂O | [4e, 4o] | 4–5 | Certified |
| Ammonia | NH₃ | [4e, 4o] | 4–5 | Certified |
| Nitrogen | N₂ | [6e, 6o] | 8 | Research |

**Suite v3.1** uses the **6-31G split-valence basis** — an upgrade from Suite v3 (STO-3G) that produces physically realistic CCSD(T) correlation energies (~5× larger than STO-3G) and is standard for NISQ-era VQE demonstrations.

All 30 certified entries in Suite v3.1 achieve `beats_classical = True`, meaning the VQE gap is smaller than the |CCSD(T) correlation energy| classical baseline.

## Leaderboard categories

| Category | Ranked by |
|----------|-----------|
| **Accuracy** | Lowest `|E_VQE − E_CASCI|` gap (Ha) |
| **Lowest Cost** | Fewest 2-qubit gates, then circuit depth |
| **Balanced** | Equal-weight normalized rank score |
| **Research** | Validated entries (gap ≥ 0.01 Ha or research-tier molecules) |

## Verifying an entry

Every leaderboard entry has a unique ID encoding the molecule, basis, mapping, and ansatz. The full JSON artifact is stored here in `releases/v3.1/db/` (or `releases/v3/db/` for STO-3G entries) and is browsable at `qencode-benchmark.org/entry/<entry_id>`.

The artifact includes:
- Molecule geometry and active space
- CASCI, HF, MP2, CCSD, CCSD(T), and VQE energies
- Qubit Hamiltonian (Pauli terms)
- Optimizer settings, multistart runs, random seed
- Tool versions (PySCF, PennyLane, SciPy, NumPy)
- SHA-256 provenance hash

## Quick start (local reproduction)

```bash
# Install dependencies (conda environment recommended)
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements.txt

# Run the full Suite v3.1 (6-31G basis, all certified molecules)
python scripts/run_suite_v3.py \
  --basis 6-31g \
  --out-dir releases/v3.1/db \
  --skip-research

# Run a single molecule
python scripts/run_suite_v3.py \
  --molecules H2 \
  --basis 6-31g \
  --out-dir releases/v3.1/db

# Generate leaderboard CSVs from results
python scripts/export_leaderboard_v3.py \
  --db-dir releases/v3.1/db \
  --suite-version 3.1

# Publish to live leaderboard (requires LEADERBOARD_PUBLISH_SECRET)
python scripts/publish_leaderboard.py \
  --secret $LEADERBOARD_PUBLISH_SECRET
```

## Repository structure

```
qencode-db/
├── benchmarks/v3/              # Suite v3 YAML definitions
├── releases/
│   ├── v3/db/                  # Suite v3 (STO-3G) entry JSONs
│   └── v3.1/db/                # Suite v3.1 (6-31G) entry JSONs
├── scripts/
│   ├── run_suite_v3.py         # Main benchmark runner (v3 / v3.1)
│   ├── generate_entry_v3.py    # Single-entry generator
│   ├── export_leaderboard_v3.py # Builds CSVs from raw results
│   ├── publish_leaderboard.py  # Pushes to live website DB
│   └── of_bridge.py            # OpenFermion parity-mapping bridge
├── website/                    # Next.js 15 site on Vercel
│   ├── app/leaderboard/        # Live leaderboard page
│   ├── app/entry/[id]/         # Per-entry verification page
│   └── lib/                    # DB access, data loading
└── schema/schema_v3.json       # Entry JSON schema
```

## Platform model

| Layer | Description |
|-------|-------------|
| Benchmark spec | Public — all molecule definitions, encoding rules, and metric formulas |
| Self-run evaluation | Anyone can reproduce results using this repository |
| Managed certification | Executed on QEncode infrastructure, independently signed |
| Public leaderboard | Certified entries only, updated after each certified run |
| Per-entry artifacts | Full JSON + SHA-256 hash linked from every leaderboard row |
| Customer dashboard | Customers track order status at qencode-benchmark.org/dashboard |

## Classical comparison

"Beats Classical" on the leaderboard means:

```
|E_VQE − E_CASCI| < |CCSD(T) correlation energy|
```

where `|CCSD(T) correlation energy| = |E_CCSD(T) − E_HF|` is the best single-reference perturbative classical result for that molecule and basis set, computed with PySCF. All 30 certified Suite v3.1 entries satisfy this criterion.
