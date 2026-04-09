# Product Walkthrough

How to use qencode-db in under two minutes.

---

## What is qencode-db?

qencode-db is a **benchmarking platform** for quantum algorithms. It lets you compare encodings (Jordan–Wigner, Bravyi–Kitaev, Parity) and ansatz types (UCCSD, hardware-efficient) on standardized molecules with certified results.

---

## Three paths

### 1. Standard Suite

**For:** Official benchmark results, certified comparisons, leaderboard-style views.

**What to do:**
1. Open the dashboard: `streamlit run scripts/streamlit_app.py`
2. Click **Standard Suite** (or select it in the sidebar)
3. Choose a molecule (e.g. H2, BeH2)
4. See: certified count, best mapping/ansatz, accuracy vs depth chart, certified table
5. Use the **Summary** panel for quick insights: best accuracy, lowest cost, best workflow

**What you get:** Certified-only results from the official benchmark suite. This is the product centerpiece.

---

### 2. Workflows

**For:** Comparing named VQE workflow strategies across molecules.

**What to do:**
1. Run workflows first (if you haven’t):
   ```bash
   python scripts/run_workflow.py --workflow vqe_standard --molecule H2
   python scripts/run_workflow.py --workflow vqe_fast --molecule H2
   ```
2. Open **Workflows** in the dashboard
3. Choose a molecule
4. See: best accuracy, best cost, best balanced workflow
5. Download the comparison table as CSV

**What you get:** Decision support: which workflow is best for accuracy, cost, or a balanced tradeoff.

---

### 3. Explore

**For:** Power users who want full tables, charts, and filters.

**What to do:**
1. Open **Explore** in the dashboard
2. Use filters: molecule, trust level, mapping, ansatz
3. Inspect the full benchmark table
4. View charts: cost vs accuracy, mapping comparison, noise impact
5. Download the table as CSV

**What you get:** Raw data and visualizations for deeper analysis.

---

## Terminology

| Term | Meaning |
|------|---------|
| **Standard Suite** | Official benchmark definition (H2, BeH2 × encodings × ansatzes) |
| **Certified results** | Entries that pass validation, trusted flag, and suite alignment |
| **Workflows** | Named VQE presets (vqe_standard, vqe_fast, vqe_noise_resilient) |
| **Cost vs accuracy** | Tradeoff between circuit depth/2Q gates and energy error |

---

## What to click first

1. **Home** → See the three paths
2. **Standard Suite** → Pick H2 or BeH2 → Look at certified table and best mapping/ansatz
3. **Workflows** → Compare vqe_standard vs vqe_fast (after running them)
4. **Explore** → Use filters and charts for deeper analysis

---

## Public platform and onboarding

- Website: https://www.qencode-benchmark.org
- Leaderboard: https://www.qencode-benchmark.org/leaderboard
- Pricing / certification: https://www.qencode-benchmark.org/pricing
- Apply for access: https://www.qencode-benchmark.org/apply
