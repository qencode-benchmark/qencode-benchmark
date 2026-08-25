# QEncode in five minutes

By the end of this page you will have produced a benchmark entry on your own machine,
checked that it reproduces, and compared it against the public leaderboard.

You need Docker, **or** Python 3.11 and about 400 MB of dependencies.

---

## 1. Install

**Docker** — the pinned environment, determinism already enforced:

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
docker build -t qencode .
```

**Or locally** — Python 3.11 (Linux/macOS/WSL2; PySCF does not build natively on Windows):

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
pip install -r requirements-v4.txt
```

---

## 2. Run your first entry

H₂ in a [2e, 2o] active space — four qubits, tapered to one. About a minute.

```bash
# Docker
docker run --rm -v "$PWD/out:/work/out" qencode \
  --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir /work/out

# Local
python scripts/generate_entry_v4.py \
  --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir out
```

Before computing anything, the pipeline runs a reproducibility guard. It refuses to
write an entry unless BLAS is single-threaded, your installed packages match
`requirements-v4.txt`, and the git tree is clean. If it stops you, that is the point —
an entry that cannot be reproduced from what it records is worse than no entry.

For a development run you can override the last two with `--allow-dirty` and
`--allow-env-drift`. Both print a warning into the run. The thread check cannot be
overridden this way, because it is the one that silently changes results.

---

## 3. Read what you produced

You now have a JSON artifact in `out/` whose filename ends in its own SHA-256:

```
H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_<hash>.json
```

The fields that matter:

```bash
python - <<'PY'
import json, glob
d = json.load(open(sorted(glob.glob("out/*.json"))[0]))
q, r, v = d["results"]["quality"], d["results"]["reference"], d["results"]["vqe"]
print("VQE energy      ", v["best_energy_hartree"], "Ha")
print("CASCI reference ", r["casci_ground_energy_hartree"], "Ha")
print("gap             ", q["abs_vqe_exact_gap"] * 1000, "mHa")
print("certified       ", q["abs_vqe_exact_gap"] < q["gap_threshold"])
print("T gates (est.)  ", d["circuit_stats"]["t_gate_estimate"])
print("BLAS threads    ", d["provenance"]["environment"]["blas_threads"])
PY
```

**The gap is the benchmark.** It is `|E_VQE − E_CASCI|`: how closely the algorithm
reconstructs the *exact* solution inside the chosen active space. It is deliberately
not a comparison against experiment or against full-system FCI — those would measure
your active space, not your algorithm. Below **10 mHartree** the entry is *certified*;
at or above, it is recorded as *research tier* and never discarded.

The entry also carries the full Pauli-decomposed Hamiltonian, the optimal parameters,
classical references (HF, MP2, CCSD, CCSD(T)), circuit and T-gate counts, and the
complete software environment — everything needed to re-run it.

---

## 4. Check that it reproduces

Run the same command again into a different directory and compare. With threads pinned
you should get the same energy to the last digit — that is the guarantee the guard buys
you.

You can also re-verify any *published* entry from this repository:

```bash
python scripts/verify_entry.py releases/v4/db/H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_93a0f8a8604d9aed.json
```

---

## 5. Compare against the leaderboard

Every certified entry is public at
**[qencode-benchmark.org/leaderboard](https://www.qencode-benchmark.org/leaderboard)**,
ranked three ways — accuracy, circuit cost, and a balanced score — with a per-entry page
showing the full artifact.

The current suite is **47 certified entries across 16 molecules**, from H₂ up to the
H₁₀ chain (20 qubits before tapering).

You can also query it directly:

```bash
curl 'https://www.qencode-benchmark.org/api/leaderboard?category=accuracy&molecule=H2'
```

---

## 6. Try something harder

```bash
# N₂ — a triple bond; needs CASSCF orbitals to partition the active space
python scripts/generate_entry_v4.py \
  --molecule N2 --mapping jordan_wigner --ansatz-type hardware_efficient \
  --orbital-opt casscf --out-dir out

# ADAPT-VQE — grows the ansatz one operator at a time; the only method
# in the suite that certifies the large hydrogen chains
python scripts/generate_entry_v4.py \
  --molecule H6 --mapping jordan_wigner --ansatz-type adapt \
  --orbital-opt casscf --out-dir out
```

`--ansatz-type` takes `uccsd`, `hardware_efficient`, or `adapt`. Larger systems
(H₈, H₁₀) use `--adapt-engine statevector --adapt-inner bfgs` and take hours, not minutes.

Full option list: `python scripts/generate_entry_v4.py --help`

---

## 7. Check your own VQE setup

The determinism problem QEncode enforces against is not specific to QEncode. If you run
VQE anywhere, this reports whether *your* environment can produce reproducible results:

```bash
python tools/check_vqe_reproducibility.py
```

It checks four things — single-threaded BLAS, recorded package versions, a recorded
seed, and a clean code version — and prints the fix for the one that usually fails.
It needs only NumPy and SciPy, and works on any codebase, not just this one.

---

## Where to go next

- **[Benchmark specification](https://www.qencode-benchmark.org/benchmark)** — the fixed definitions
- **[Methodology](https://www.qencode-benchmark.org/methodology)** — active spaces, references, metric
- **[Why threading breaks VQE](https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug)** — the finding that shaped this suite

Questions, a result you would like listed, or a molecule you think belongs in the
suite: **support@qencode-benchmark.org**. Contributions and issues are welcome.
