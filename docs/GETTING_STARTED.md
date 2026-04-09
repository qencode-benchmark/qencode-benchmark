# Getting started: qencode-db

Step-by-step setup and run instructions.

---

## 1. Software you need

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.10, 3.11, or 3.12 | Run scripts and pipeline |
| **pip** | (comes with Python) | Install dependencies |
| **Git** | (optional) | Clone repo / use version control |

**Check you have Python:**

```powershell
# Windows (PowerShell or Command Prompt)
python --version
```

If you see `Python 3.10` or higher, you’re good. If not, install from [python.org](https://www.python.org/downloads/). During install, enable **“Add Python to PATH”**.

---

## 2. Get the project (if needed)

```powershell
# If you use Git
git clone https://github.com/qencode-benchmark/qencode-benchmark.git
cd qencode-benchmark

# Or: you already have the folder (e.g. qencode-db). Open a terminal there.
cd "C:\Users\jlaba\Documents\qencode-db"
```

Official platform links:

- https://www.qencode-benchmark.org
- https://www.qencode-benchmark.org/pricing
- https://www.qencode-benchmark.org/apply

---

## 3. Create a virtual environment and install deps

**Windows (PowerShell):**

```powershell
# 1. Go to project folder
cd "C:\Users\jlaba\Documents\qencode-db"

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
.\.venv\Scripts\Activate.ps1

# If you get “execution of scripts is disabled”, run once:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 4. Upgrade pip (recommended)
python -m pip install --upgrade pip

# 5. Install dependencies

# Option A – full (includes PySCF for generating new entries)
pip install -r requirements.txt

# Option B – if that fails on Windows (PySCF build error), use core only:
# pip install -r requirements-core.txt
# You can run check, query, v2-only. gen-h2 / add-entry need PySCF (see Troubleshooting).
```

**Linux / macOS:**

```bash
cd /path/to/qencode-db
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install --upgrade pip
pip install -r requirements.txt
```

**Check install (full):**  
`python -c "import qiskit_nature, pyscf, jsonschema; print('OK')"`

**Check install (core only):**  
`python -c "import qiskit_nature, jsonschema; print('OK')"`  
If that prints `OK`, you’re ready.

---

### 3b. Conda + PySCF (full project)

You need **PySCF** for gen-h2 / add-entry. Conda-forge provides PySCF only for **Linux and macOS**, not native Windows.

---

#### Option A: WSL + Conda (recommended on Windows)

Use Linux inside Windows via [WSL](https://docs.microsoft.com/en-us/windows/wsl/install). Then Conda can install PySCF from conda-forge.

**1. Install WSL and Ubuntu** (if you don’t have it):

```powershell
# In PowerShell (Admin optional)
wsl --install -d Ubuntu
```

Restart if asked, then open **Ubuntu** from the Start menu.

**2. Inside Ubuntu (WSL):**

```bash
# Install Miniconda (one-time)
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda3
echo 'export PATH="$HOME/miniconda3/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or use existing Conda if you installed it for WSL

# Go to your project (Windows path under WSL)
cd /mnt/c/Users/jlaba/Documents/qencode-db

# Create conda env and install PySCF + deps
conda env create -f environment.yml
conda activate qencode

# Verify
python -c "import qiskit_nature, pyscf, jsonschema; print('OK')"
```

**3. Run the project** (always in WSL, with `conda activate qencode`):

```bash
python scripts/run_pipeline.py check
python scripts/run_pipeline.py gen-h2
python scripts/query_db.py --db-dir releases/v2/db --molecule H2
```

---

#### Option B: Conda on Linux or macOS

Conda-forge has PySCF for Linux and macOS. Use the same steps as in Option A (without WSL):

```bash
cd /path/to/qencode-db
conda env create -f environment.yml
conda activate qencode
python -c "import qiskit_nature, pyscf, jsonschema; print('OK')"
```

---

#### Option C: Windows native (no WSL) – VS Build Tools + pip

If you stay on **native Windows** (no WSL):

1. Install [Build Tools for Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/) with **“Desktop development with C++”** (includes `nmake`, MSVC).
2. Open a **new** terminal, then:

```powershell
cd "C:\Users\jlaba\Documents\qencode-db"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "import qiskit_nature, pyscf, jsonschema; print('OK')"
```

PySCF will build from source. If the build still fails, use **Option A (WSL + Conda)**.

---

## 4. Run the pipeline

All commands below assume you’re in the **project folder** (repo root) and the venv is activated.

### Where the files are

| Location | Contents |
|----------|----------|
| **Repo root** | `molecules_v2.json`, `schema/`, `scripts/`, `Makefile`, `requirements.txt` |
| `releases/v1/db/` | v1 entries (legacy) |
| `releases/v2/db/` | v2 entries, `index.json`, `benchmarks.csv`, `manifest.json` |
| `releases/v2/trusted/` | Trusted subset (`make trusted`) |
| `releases/$(VERSION)_local/` | Release tarballs + SHA256SUMS (e.g. `VERSION=2.0.1` → `releases/2.0.1_local/`) |

Use **`VERSION=2.0.1`** for release commands:  
`make release-local VERSION=2.0.1`, `make release-test VERSION=2.0.1`, `make release-full VERSION=2.0.1`.

### 4.1 Full pipeline (validate, migrate, index, trusted, supply-chain)

**Windows:**

```powershell
python scripts/run_pipeline.py check
```

**Linux/macOS (with Make):**

```bash
make check
```

This runs: v1 validate → migrate v1→v2 → v2 validate → index → benchmarks → audit → trusted export → manifest + hashes + verify.

---

### 4.2 Query existing entries

**List all entries:**

```powershell
python scripts/query_db.py --db-dir releases/v2/db
```

**Filter by molecule (e.g. H2):**

```powershell
python scripts/query_db.py --db-dir releases/v2/db --molecule H2
```

**Only trusted entries:**

```powershell
python scripts/query_db.py --db-dir releases/v2/db --trusted-only
```

**Export to CSV:**

```powershell
python scripts/query_db.py --db-dir releases/v2/db -o results.csv --format csv
```

**Same via run_pipeline:**

```powershell
python scripts/run_pipeline.py query --molecule H2 --trusted-only
python scripts/run_pipeline.py query --output results.csv --format csv
```

---

### 4.3 Add a new benchmark entry (generate → validate → index)

**1. Generate one entry (e.g. H2, sto3g, Jordan–Wigner, UCCSD):**

```powershell
python scripts/run_pipeline.py add-entry --molecule H2 --basis sto3g
```

**2. Or use shortcuts:**

```powershell
# H2 sto3g JW UCCSD + exact energy
python scripts/run_pipeline.py gen-h2

# LiH sto3g JW UCCSD
python scripts/run_pipeline.py gen-lih
```

**3. Refresh index and audit (without re-migrating from v1):**

```powershell
python scripts/run_pipeline.py v2-only
```

**4. (Optional) Export trusted set and update supply-chain:**

On Windows you’d run the underlying scripts (or use `check_all` with the right flags).  
On Linux/macOS:

```bash
make v2-only
make trusted
make supplychain
make supplychain-verify
```

---

### 4.4 Regenerate everything from scratch

Same as “full pipeline”:

**Windows:**  
`python scripts/run_pipeline.py check`  
or  
`python scripts/run_pipeline.py regenerate`

**Linux/macOS:**  
`make check`  
or  
`make regenerate`

---

## 5. Quick reference – what to run when

| Goal | Windows | Linux/macOS |
|------|---------|-------------|
| Setup once (pip) | `python -m venv .venv` → activate → `pip install -r requirements.txt` | Same |
| Setup once (Conda + PySCF) | **WSL** (or Linux/macOS): `conda env create -f environment.yml` → `conda activate qencode` | Same |
| Full pipeline | `python scripts/run_pipeline.py check` | `make check` |
| Query DB | `python scripts/query_db.py --db-dir releases/v2/db [--molecule H2] [--trusted-only]` | Same |
| List molecule/variant options | `python scripts/run_pipeline.py list-catalog` or `python scripts/generate_entry_v2.py --list-molecules` | `make list-catalog` |
| Add H2 entry | `python scripts/run_pipeline.py gen-h2` | `make gen-h2` |
| Add LiH / BeH2 | `python scripts/run_pipeline.py gen-lih` / `gen-beh2` | `make gen-lih` / `make gen-beh2` |
| Add custom entry | `python scripts/run_pipeline.py add-entry --molecule LiH [--variant geom] --basis sto3g` | `make add-entry MOLECULE=LiH [VARIANT=geom] BASIS=sto3g` |
| Query by depth | `python scripts/query_db.py --max-depth 10 --sort 2q` | Same |
| Refresh v2 only (no migrate) | `python scripts/run_pipeline.py v2-only` | `make v2-only` |
| Run VQE on entries | `python scripts/run_vqe_v2.py --db-dir releases/v2/db --skip-existing` | `make run-vqe DB_DIR=releases/v2/db` |
| Release local (VERSION=2.0.1) | `make release-local VERSION=2.0.1` (WSL) | `make release-local VERSION=2.0.1` |
| Release full (check + local + test) | `make release-full VERSION=2.0.1` (WSL) | `make release-full VERSION=2.0.1` |
| Smoke test (schema + VQE H2 + manifest/hashes + trusted) | `bash scripts/smoke.sh` | `make smoke` |
| bench-mvp (gen + VQE + trusted + verify) | — | `make bench-mvp` |
| bench (matrix: gen + VQE + trusted + report-comparison) | `python scripts/run_pipeline.py bench [--matrix ...]` | `make bench MATRIX=...` |
| report-comparison (JW vs parity vs BK) | `python scripts/run_pipeline.py report-comparison` | `make report-comparison` |

**Circuit metrics (hardware-relevant depth/2q):**  
After VQE, run `python scripts/compute_circuit_metrics_v2.py --db-dir releases/v2/db` to bind parameters, transpile to basis gates (cx, rz, sx, x), and write `circuit_stats.ansatz_depth_transpiled` and `ansatz_num_2q_gates_transpiled`. The comparison report then uses these when present.

**Canonical set (dedupe per cell):**  
Run `python scripts/select_canonical_v2.py --db-dir releases/v2/db` to write `releases/v2/db/canonical_index.json` (one chosen entry per molecule/variant/basis/mapping/ansatz). Optionally `--copy-to releases/v2/canonical`. Then run trusted export or report on that set:  
`python scripts/export_trusted_v2.py --db-dir releases/v2/canonical --out-dir releases/v2/trusted`  
or use `--canonical-index releases/v2/db/canonical_index.json` with the full db dir so only canonical entries are considered.

**LiH/BeH2 VQE quality:**  
`run_vqe_v2.py` uses maxiter=2000 and stores a convergence trace for LiH by default; use `--optimizer SLSQP` or `--optimizer Nelder-Mead` to try other optimizers.

**Shot-based and noisy VQE (MVP: H2, BeH2):**  
Requires `qiskit-aer`. Shot-based: `python scripts/run_vqe_v2.py --db-dir releases/v2/db --mode shots --shots 4096 --pattern "H2*"`. Noisy: `--noise depolarizing --p1 0.001 --p2 0.01`. ZNE mitigation: `--noise depolarizing --mitigation zne`. Results go to `results.vqe_shots`, `results.vqe_noisy`, `results.vqe_mitigated`; the comparison report includes `gap_ideal`, `gap_shots`, `gap_noisy`, `gap_mitigated` and stderrs. Backend is stored as `aer_estimator_shots` (shots) or `aer_estimator` (noisy). When exact is missing, report gaps are blank and `exact_missing` is set.

**Measurement grouping (QWC):**  
To reduce measurement cost (e.g. LiH with hundreds of Pauli terms), use `--grouping qwc` with `--mode shots` or `--noise`. Use a **real entry path** — do not copy a literal like `<LiH_entry>.json` (the shell treats `<...>` as redirection). Examples:

```bash
# Single LiH entry (pick any LiH file from releases/v2/db; names contain sha256)
python scripts/run_vqe_v2.py --file releases/v2/db/LiH_sto3g_JW_uccsd_v2__sha256_178d772bf8f4d2fe.json --mode shots --shots 4096 --grouping qwc --maxiter 50

# Or run on all LiH entries (slower)
python scripts/run_vqe_v2.py --db-dir releases/v2/db --pattern "LiH*v2*.json" --mode shots --shots 4096 --grouping qwc --maxiter 50
```

After such a run, the entry gets `execution.measurement` (num_terms, num_groups, shots_per_group, estimated_shots_total). The comparison report **terms** and **groups** columns show "—" until at least one entry in the DB was run with `--grouping qwc`; then those rows show the reduction (e.g. "631 terms → 45 groups").

**Canonical-by-default reports:**  
Comparison report uses `releases/v2/db/canonical_index.json` by default when it exists (one entry per cell). Use `--no-canonical` to include all entries.

**Client demo (one repeatable sequence):**  
From repo root, with venv active and `qiskit-aer` installed:

```powershell
# 1) Pick one canonical entry per cell (if not already done)
python scripts/select_canonical_v2.py --db-dir releases/v2/db --output releases/v2/db/canonical_index.json

# 2) Optional: run noisy + ZNE on H2-only (demo matrix: benchmarks/matrix_noisy_demo.json)
python scripts/run_vqe_v2.py --db-dir releases/v2/db --matrix benchmarks/matrix_noisy_demo.json --noise depolarizing --p1 0.001 --p2 0.01 --mitigation zne --pattern "H2*"

# 3) Comparison report (uses canonical index by default) + CSV
python scripts/report_comparison_v2.py --db-dir releases/v2/db --csv --output releases/v2/db/comparison_mapping.csv
```

The report prints a summary table to the terminal and writes `comparison_mapping.csv` with ideal vs noisy vs mitigated gaps, stderrs, and transpiled depth/2q. For a tiny demo, use `--db-dir releases/v2/canonical` after `--copy-to releases/v2/canonical` in step 1.

---

## 6. Troubleshooting

- **`python` not found**  
  Install Python and ensure “Add to PATH” is checked. Restart the terminal.

- **`Activate.ps1` execution disabled (Windows)**  
  Run in PowerShell (as yourself):  
  `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

- **`No module named 'qiskit_nature'` or `'pyscf'`**  
  Activate the venv and run `pip install -r requirements.txt` again.  
  On Windows, if PySCF fails to build, use `pip install -r requirements-core.txt` instead (see below).

- **PySCF fails to build on Windows** (`Building wheel for pyscf ... error`, `nmake` / `CMAKE_C_COMPILER` errors)  
  PySCF needs C/C++ build tools. Easiest workaround:

  1. **Use core deps only (no PySCF):**
     ```powershell
     pip install -r requirements-core.txt
     ```
     You can run **check**, **query**, **v2-only**. You cannot run **gen-h2** or **add-entry** (those need PySCF).

  2. **To enable generation on Windows:** Use **WSL + Conda** (see **section 3b**, Option A) so PySCF installs from conda-forge. Alternatively: **VS Build Tools + pip** (Option C) or **WSL + pip**.

- **`.venv` from Linux doesn’t work on Windows**  
  Delete `.venv` and create a new one on Windows:  
  `python -m venv .venv`  
  then activate and `pip install -r requirements.txt` (or `requirements-core.txt`).

- **`make` not found (Windows)**  
  Use the Python commands (e.g. `python scripts/run_pipeline.py ...`) instead of `make`. Or use WSL / Git Bash if you want `make`.

- **`AttributeError: module 'numpy' has no attribute 'in1d'`** (Bravyi–Kitaev mapping)  
  NumPy 2.x removed `np.in1d` from the top-level namespace; qiskit-nature’s BravyiKitaevMapper uses it.  
  `generate_entry_v2.py` includes a compat shim (`np.in1d = np.isin`) at import time. Ensure you run with the project’s script (not an older copy). If you still see this, pin `numpy<2` in your environment.

---

## 7. Project layout (useful paths)

- **DB (v2):** `releases/v2/db/` — entries, `index.json`, manifest, hashes  
- **Trusted subset:** `releases/v2/trusted/`  
- **Molecule catalog:** `molecules_v2.json` or `molecules_v1.json` in project root  
- **Schema:** `schema/schema_v2.json`  
- **Scripts:** `scripts/` — `run_pipeline.py`, `query_db.py`, `generate_entry_v2.py`, etc.

For more detail, see [CATALOG.md](CATALOG.md) and [README.md](../README.md).
