# Getting Started with QEncode

This guide walks you through installing dependencies and preparing your environment before running the benchmark suite.

---

## Requirements

- Python 3.8 or higher
- pip

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark-suite.git
cd qencode-benchmark-suite
```

---

## Step 2 — Install dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

At minimum, the Standard Suite v1 requires **PyYAML** and **PySCF**:

```bash
pip install pyyaml pyscf qiskit qiskit-nature
```

> **Note:** If you are on Apple Silicon (M1/M2) or a restricted environment, see the platform notes below.

---

## Step 3 — Verify your installation

Run a quick check to confirm everything is set up correctly:

```bash
python scripts/run_qencode_benchmark.py --molecule H2 --skip-audit
```

You should see output confirming the H2 benchmark completed and results written to `artifacts/`.

---

## Step 4 — Run the full benchmark suite

Once verified, run the full Standard Suite v1:

```bash
python scripts/run_qencode_benchmark.py
```

This runs all molecules (H2, BeH2, HF) across all encoding and ansatz combinations and produces the leaderboard dataset.

See [QUICK_START.md](QUICK_START.md) for all available flags and options.

---

## Platform Notes

**Windows:** Use WSL2 (Windows Subsystem for Linux) for best compatibility with PySCF.

**Apple Silicon (M1/M2):** Install PySCF via conda:
```bash
conda install -c conda-forge pyscf
```

**Linux (Ubuntu/Debian):** No special steps required.

---

## Next Steps

- Read the [Benchmark Specification](../docs/Benchmark%20specification%20v1.pdf) to understand fixed configurations
- Check the [Leaderboard Rules](LEADERBOARD_RULES_V1.md) before submitting results
- Visit [qencode-benchmark.org](https://qencode-benchmark.org) to view the public leaderboard
- To get your results certified, see [Get Certified](https://qencode-benchmark.org/certify)

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'pyscf'`**
Run `pip install pyscf` and retry.

**`ModuleNotFoundError: No module named 'yaml'`**
Run `pip install pyyaml` and retry.

**Results differ from the leaderboard values**
Ensure you are using the exact molecule geometry and basis set defined in the benchmark spec. Any deviation from the fixed configuration will produce non-comparable results by design.

---

For further help, open an issue on [GitHub](https://github.com/qencode-benchmark/qencode-benchmark-suite/issues) or email [support@qencode-benchmark.org](mailto:support@qencode-benchmark.org).
