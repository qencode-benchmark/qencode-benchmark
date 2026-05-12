# Verifying a QEncode Entry

Every certified entry can be independently reproduced. The SHA-256 provenance hash
locks the result to exact tool versions, geometry, and optimizer seed.

---

## 1. Find the entry you want to verify

Go to [qencode-benchmark.org/leaderboard](https://www.qencode-benchmark.org/leaderboard)
and click **Details** on any row. The entry page shows:

- Full molecule geometry and active space
- All energies (HF, MP2, CCSD, CCSD(T), CASCI, VQE)
- Qubit mapping, ansatz type, circuit stats
- Optimizer settings and multistart runs
- Tool versions
- SHA-256 provenance hash
- Exact reproduce command

---

## 2. Set up the environment

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark.git
cd qencode-benchmark
conda create -n qencode python=3.11
conda activate qencode
pip install -r requirements.txt
```

---

## 3. Run the reproduce command

Copy the command from the entry's Details page, for example:

```bash
python scripts/generate_entry_v3.py \
  --molecule LiH \
  --basis 6-31g \
  --mapping bk \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42
```

---

## 4. Check the hash

The script prints `entry_hash_sha256` at the end. Compare it with the value shown
on the entry's Details page (and stored in `releases/v3.1/db/<entry_id>.json`).

A matching hash confirms the result is bit-for-bit reproducible with the same
tool versions.

---

## Raw JSON

Every entry JSON is publicly accessible at:

```
https://raw.githubusercontent.com/qencode-benchmark/qencode-benchmark/master/releases/v3.1/db/<entry_id>.json
```

The entry Details page also has a **View raw JSON on GitHub** link.
