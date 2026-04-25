# QEncode — Quantum Algorithm Benchmarking Standard

**QEncode is the standard for reproducible VQE evaluation, managed benchmark execution, and signed certification of quantum chemistry algorithms.**

🌐 **[qencode-benchmark.org](https://www.qencode-benchmark.org)** &nbsp;·&nbsp; 📊 **[Live Leaderboard](https://www.qencode-benchmark.org/leaderboard)** &nbsp;·&nbsp; 📄 **[Benchmark Spec](https://www.qencode-benchmark.org/benchmark)** &nbsp;·&nbsp; 💰 **[Pricing](https://www.qencode-benchmark.org/pricing)**

---

## What QEncode does

Most published VQE results cannot be independently reproduced — different teams use different molecules, encodings, error metrics, and hardware. QEncode fixes this with:

- **Fixed benchmark definitions** — 5 molecules (H₂, LiH, HF, N₂, BeH₂), 3 qubit encodings (Jordan-Wigner, parity, Bravyi-Kitaev), 2 ansatz families (UCCSD, HEA), exact FCI reference energies
- **Managed execution** — benchmarks run on verified, reproducible infrastructure under identical conditions
- **Signed certification** — results are signed with Ed25519, producing a verifiable certification receipt
- **Public leaderboard** — certified entries appear on the live leaderboard, ranked by accuracy gap, circuit cost, and a balanced score

## Suite v2 benchmark molecules

| Molecule | Formula | Qubits (JW) | Status |
|----------|---------|-------------|--------|
| Hydrogen | H₂ | 4 | Active |
| Lithium Hydride | LiH | 12 | Active |
| Hydrogen Fluoride | HF | 12 | Active |
| Beryllium Hydride | BeH₂ | 14 | Active |
| Nitrogen | N₂ | active-space dependent | Active |

All molecules use STO-3G basis (cc-pVDZ for larger systems). Reference energies computed with PySCF Full-CI.

## Platform model

| Layer | Description |
|-------|-------------|
| Benchmark spec | Public — all molecule definitions, encoding rules, and metric formulas |
| Self-run evaluation | Anyone can run locally using this repository |
| Managed certification | Executed on QEncode infrastructure, independently verified, signed receipt |
| Public leaderboard | Certified entries only, updated after each certified run |
| Customer dashboard | Customers track order status at qencode-benchmark.org/dashboard |

## Leaderboard categories

- **Accuracy** — ranked by energy gap to FCI (lower = better)
- **Cost** — ranked by circuit depth and two-qubit gate count (lower = better)
- **Balanced** — normalized combination of accuracy and cost

## Quick start (local run)

```bash
# Install dependencies (conda environment recommended)
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements.txt

# Run the full Suite v2
python scripts/run_standard_suite.py --suite benchmarks/standard/suite_v2.yaml --out-dir releases/v2/db

# Run a single molecule
python scripts/run_standard_suite.py --suite benchmarks/standard/suite_v2.yaml --out-dir releases/v2/db --molecule H2

# Generate leaderboard CSVs from results
python scripts/generate_leaderboard.py

# Publish to live leaderboard (requires LEADERBOARD_PUBLISH_SECRET)
python scripts/publish_leaderboard_live.py
```

## Repository structure

```
qencode-db/
├── benchmarks/standard/        # Suite v2 YAML definitions
├── datasets/leaderboard/       # Generated leaderboard CSVs
├── releases/v2/db/             # Raw benchmark output JSONs
├── scripts/                    # Benchmark, generation, and publish tooling
│   ├── run_standard_suite.py   # Main benchmark runner
│   ├── generate_leaderboard.py # Builds CSVs from raw results
│   ├── publish_leaderboard_live.py  # Pushes to live website
│   └── job_poller.py           # Ubuntu daemon for automated job queue
├── docs/                       # Technical documentation
└── website/                    # Next.js 15 site on Vercel
    ├── app/                    # App Router pages and API routes
    ├── lib/db.js               # Neon Postgres layer
    └── lib/email.js            # Resend transactional emails
```

## Tech stack

| Component | Technology |
|-----------|------------|
| Website | Next.js 15, React 19, Tailwind CSS, deployed on Vercel |
| Database | Neon Postgres (via @neondatabase/serverless) |
| Auth | Clerk v6 |
| Payments | Lemon Squeezy (webhooks → automated job queue) |
| Email | Resend |
| Execution | Python 3.11, Qiskit, Qiskit-Aer, PySCF |
| Certification | Ed25519 signing |
| Job queue | systemd service (Ubuntu) polling Postgres via REST API |

## Documentation

- [Benchmark Specification](https://www.qencode-benchmark.org/benchmark)
- [Leaderboard Rules](docs/LEADERBOARD_RULES_V1.md)
- [Standard Suite v2](docs/STANDARD_SUITE_V2.md)
- [Getting Started](docs/GETTING_STARTED.md)

## Links

- Website: https://www.qencode-benchmark.org
- Leaderboard: https://www.qencode-benchmark.org/leaderboard
- Pricing: https://www.qencode-benchmark.org/pricing
- Blog: https://www.qencode-benchmark.org/blog
- Contact: support@qencode-benchmark.org
