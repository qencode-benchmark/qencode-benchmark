# QEncode — Quantum Algorithm Benchmarking Standard

QEncode is an open benchmarking standard for quantum chemistry algorithms. It provides fixed, reproducible VQE benchmarks across H₂, BeH₂, and HF — with LiH coming in Suite v2 — enabling fair comparison of encodings, ansatz types, and algorithm implementations.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Suite Version](https://img.shields.io/badge/Suite-v2-green.svg)](https://qencode-benchmark.org/benchmark)
[![Leaderboard](https://img.shields.io/badge/Leaderboard-Live-brightgreen.svg)](https://qencode-benchmark.org/leaderboard)

---

## Problem

Quantum algorithm benchmarking today is inconsistent and difficult to reproduce.

Different studies use different:

- Encodings (Jordan-Wigner, Bravyi-Kitaev, Parity)
- Ansatz circuits (UCCSD, HEA, custom)
- Noise models and hardware backends
- Optimizers and convergence criteria
- Evaluation metrics

This makes results impossible to compare across experiments, slowing meaningful progress in the field.

---

## Solution

QEncode provides a structured benchmarking framework with:

- **Standard Benchmark Suite (v2)** — fixed molecule geometry, basis set, encoding, and ansatz
- **Certified Results** — verified outputs with reproducibility guarantees and signed receipts
- **Public Leaderboard** — compare algorithms across accuracy, hardware cost, and balanced score
- **Reproducible Datasets** — open data for every benchmark run, versioned and traceable
- **Workflow Evaluation** — compare complete algorithm configurations, not just individual parameters

---

## Molecules (Suite v2)

| Molecule | Status | Qubits |
|---|---|---|
| H₂ (Hydrogen) | ✅ Active | 4 |
| BeH₂ (Beryllium Hydride) | ✅ Active | 14 |
| HF (Hydrogen Fluoride) | ✅ Active | 12 |
| LiH (Lithium Hydride) | 🔜 Suite v2 | 12 |

---

## Quick Start

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark-suite.git
cd qencode-benchmark-suite
pip install pyyaml pyscf qiskit qiskit-nature
python scripts/run_qencode_benchmark.py
```

Run a single molecule:

```bash
python scripts/run_qencode_benchmark.py --molecule H2
```

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for full setup instructions and platform notes.

---

## Certification

Anyone can run the benchmark suite locally. **Official certification** — with a signed receipt and eligibility for public leaderboard inclusion — is available at [qencode-benchmark.org/certify](https://qencode-benchmark.org/certify).

| Tier | Price | Scope |
|---|---|---|
| Single-Molecule | $1,500 | One molecule, signed receipt + benchmark report |
| Full Suite v2 | $4,000 | All molecules, signed receipt + audit-ready artifacts |

Certified results are the only entries accepted on the official public leaderboard.

---

## Leaderboard

View live rankings at [qencode-benchmark.org/leaderboard](https://qencode-benchmark.org/leaderboard).

Rankings are available in three categories:

- **Best Accuracy** — lowest energy error gap vs. exact classical reference
- **Lowest Hardware Cost** — fewest two-qubit gates
- **Best Balanced Score** — combined accuracy and cost metric

---

## Repository Structure

```
qencode-benchmark-suite/
├── benchmarks/standard/      # Fixed benchmark definitions (Suite v1, v2)
├── datasets/                 # Reference datasets and leaderboard snapshots
├── artifacts/                # Generated leaderboard reports and audit logs
├── docs/
│   ├── GETTING_STARTED.md    # Environment setup and installation
│   ├── QUICK_START.md        # One-command benchmark execution
│   ├── LEADERBOARD_RULES_V1.md
│   ├── whitepaper/           # Full technical specification (PDF)
│   └── Benchmark specification v1.pdf
├── CITATION.cff              # Citation metadata for academic use
└── LICENSE
```

---

## Citing QEncode

If you use QEncode in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff):

```bibtex
@software{qencode2026,
  title  = {QEncode Benchmark Suite},
  url    = {https://qencode-benchmark.org},
  year   = {2026}
}
```

---

## Contributing

QEncode is open source. We welcome issues, discussions, and pull requests. If you have suggestions for additional molecules, encodings, or scoring metrics, please open an issue.

---

## Links

- 🌐 Website: [qencode-benchmark.org](https://qencode-benchmark.org)
- 📊 Leaderboard: [qencode-benchmark.org/leaderboard](https://qencode-benchmark.org/leaderboard)
- 📄 Docs: [qencode-benchmark.org/docs](https://qencode-benchmark.org/docs)
- 🏅 Get Certified: [qencode-benchmark.org/certify](https://qencode-benchmark.org/certify)
- 📧 Contact: [jlabquantumc@gmail.com](mailto:jlabquantumc@gmail.com)
