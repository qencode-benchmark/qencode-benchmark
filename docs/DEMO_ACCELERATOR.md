# Accelerator Demo — 3–5 Minute Flow

Use this script for a polished product demo (investors, accelerators, partners).

---

## Prerequisites

- Python 3.9+ with venv activated
- `pip install -r requirements.txt` (PySCF, Qiskit)
- `pip install -r requirements-dashboard.txt` (Streamlit, Plotly, Pandas)
- Pre-run standard suite and trust levels (or use existing `releases/v2/db` data)

---

## Demo Script

### 1. Open the dashboard (30 sec)

```bash
streamlit run scripts/streamlit_app.py
```

*Open http://localhost:8501*

> "qencode-db has three paths. We start with the product centerpiece: certified benchmark results."

---

### 2. Standard Suite (1.5 min)

1. Click **Standard Suite** (or use sidebar)
2. Point out: **Certified results** count, suite version
3. Select **H2**
4. Show the **Summary** panel: best certified accuracy, lowest cost, best workflow (if available)
5. Show **Best mapping** and **Best ansatz** for certified results
6. Show **Cost vs accuracy** chart
7. Show **Certified results table** and CSV download

> "This is our official benchmark suite. Only certified entries—validated, trusted, in-suite—appear here. You can see which encoding and ansatz give the best accuracy or lowest circuit cost."

---

### 3. Workflows (1 min)

1. Click **Workflows**
2. If results exist: select **H2**, show best accuracy / best cost / best balanced
3. If no results: show the "Run workflows first" message and the commands

> "Workflows are named VQE strategies. You run them on a molecule, then compare: which workflow gives best accuracy, which gives lowest cost, which is best balanced."

---

### 4. Explore (1 min)

1. Click **Explore**
2. Show the full benchmark table with filters
3. Show molecule, trust, mapping, ansatz filters
4. Show charts: cost vs accuracy, mapping comparison, noise impact
5. Download CSV

> "For power users, Explore gives full tables, advanced filters, and charts. Everything is exportable."

---

### 5. Summary (30 sec)

> "qencode-db gives you: certified benchmark results, workflow comparison, and full data exploration. Same molecules, same metrics—fair comparisons across encodings and ansätze. Demo-friendly and accelerator-ready."

---

## Fallback (no data)

If `releases/v2/db` is empty:

1. Run a quick benchmark: `python scripts/run_matrix.py --molecule H2 --encodings JW,BK --ansatz UCCSD`
2. Assign trust levels: `python scripts/assign_trust_levels.py --db-dir releases/v2/db`
3. Sync: `python scripts/compare.py --molecule H2 --sync`
4. Then run the dashboard demo

---

## Commercial CTA (for live demos)

After the technical demo, point users to:

- Pricing / certification: https://www.qencode-benchmark.org/pricing
- Apply for access: https://www.qencode-benchmark.org/apply
