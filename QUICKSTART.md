# QEncode in five minutes

By the end of this page you will have scored a VQE energy against the reference, produced
a benchmark entry on your own machine, checked that it reproduces, and compared it against
the public leaderboard.

You need Python 3.10+, **or** Docker. If you only want to score a result you already have,
you need neither a clone nor a chemistry stack — start at §1.

---

## 1. Score a result you already have

If you already ran a VQE and want to know what the number is worth, this is the whole
thing. It needs no clone, no chemistry stack, and no network.

```bash
pip install qencode-benchmark
```

```python
import qencode

s = qencode.score(-7.9835,               # your energy, in Hartree
                  molecule="LiH",
                  active_space=(4, 4),   # checked, not assumed
                  optimizer="COBYLA",
                  ansatz="hea")
print(s.report())
```

```
  your energy             -7.9835000000 Ha
  exact ground state      -7.9837729770 Ha   (CASCI in the declared active space)
  gap                      0.0002729770 Ha   = 0.273 mHa

  reaches CHEMICAL ACCURACY (< 1.6 mHa) and would meet the 10 mHa certification threshold
  margin             9.727e-03 Ha (97.3% of the threshold)

  optimiser          COBYLA (gradient-free)
  amplifying         YES -- gradient-free optimiser on an unstructured ansatz
  among published    #3 of 4 QEncode entries for this problem
```

The comparison needs the exact ground state of *your* active space, which normally means
installing PySCF and waiting. QEncode ships those references for all 16 suite molecules
inside the package, so the call is a file read.

It refuses rather than guesses: a declared active space that does not match the reference
raises, and an energy below the variational minimum is reported as a problem with your
setup before any gap is quoted. `qencode.available()` lists what can be scored.

**Scoring is not certification.** It tells you a self-reported number would meet the
threshold. Certification is what §2 onward produces. See
[docs/TRUST_POLICY.md](docs/TRUST_POLICY.md).

Walkthrough with executed output:
[notebooks/score_your_vqe_result.ipynb](notebooks/score_your_vqe_result.ipynb) ·
Full guide: <https://www.qencode-benchmark.org/score>

---

## 2. Install the pipeline

Generating an entry — as opposed to scoring one — runs PySCF and PennyLane, so it needs
the chemistry stack.

**pip** — Python 3.10+ (Linux/macOS/WSL2):

```bash
pip install qencode-benchmark
```

That installs the pinned stack and puts a `qencode` command on your path. It works without
a clone: the molecule catalogue ships with the package. Working from a clone additionally
gives you the entry database and full provenance, since an entry records the git commit
that produced it:

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
pip install -e .
```

**Docker** — the pinned environment, determinism already enforced:

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark
docker build -t qencode .
```

Check which mode you are in with `qencode where`.

> **Windows:** PySCF has no native Windows wheels. Use **WSL2 + Ubuntu**
> (`wsl --install -d Ubuntu` in PowerShell, once), then follow the Linux instructions
> inside Ubuntu. Scoring (§1) is pure Python and works natively on Windows.

---

## 3. Run your first entry

H₂ in a [2e, 2o] active space — four qubits, tapered to one. About ten seconds.

```bash
# pip
qencode run --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir out

# Docker
docker run --rm -v "$PWD/out:/work/out" qencode \
  --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir /work/out

# from a clone, without installing
python scripts/generate_entry_v4.py \
  --molecule H2 --mapping jordan_wigner --ansatz-type uccsd --out-dir out
```

All three run the same code. Or from Python:

```python
import qencode

entry = qencode.generate_entry(molecule="H2", out_dir="out")
print(qencode.gap_mha(entry), "mHa from exact")
print(qencode.entry_hash(entry))
```

Before computing anything, the pipeline runs a reproducibility guard. It refuses to write
an entry unless BLAS is single-threaded, your installed packages match
`requirements-v4.txt`, and the git tree is clean. If it stops you, that is the point — an
entry that cannot be reproduced from what it records is worse than no entry.

For a development run you can override the last two with `--allow-dirty` and
`--allow-env-drift`. Both print a warning into the run. The thread check cannot be
overridden this way, because it is the one that silently changes results.

### The flags you will actually use

| Flag | Default | Notes |
|---|---|---|
| `--molecule` | `H2` | One of the 16 below |
| `--mapping` | `jordan_wigner` | `jordan_wigner` \| `parity` \| `bravyi_kitaev` |
| `--ansatz-type` | `uccsd` | `uccsd` \| `hardware_efficient` \| `adapt` |
| `--orbital-opt` | `hf` | `casscf` is required for N₂, C₄H₄, H₆, H₈, H₁₀ and benzene |
| `--multistart` | `3` | Random restarts |
| `--max-iter` | `500` | Optimiser iterations per restart |
| `--reps` | `2` | HEA layer count (`hardware_efficient` only) |
| `--backend` | `default.qubit` | `lightning.*` is permitted for gradient-based entries only — see [rules](docs/LEADERBOARD_RULES_V2.md) |
| `--out-dir` | `releases/v4/db` | Where the entry JSON is written |

Full list: `qencode run --help`.

**Molecules:** H₂, HF, LiH, BeH₂, H₂O, NH₃, H₄, H₂CO, C₄H₆, C₄H₄, (H₂O)₂, N₂, H₆,
benzene, H₈, H₁₀.

---

## 4. Read what you produced

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
reconstructs the *exact* solution inside the chosen active space. It is deliberately not a
comparison against experiment or against full-system FCI — those would measure your active
space, not your algorithm. Below **10 mHartree** the entry is *certified*; at or above, it
is recorded as *research tier* and never discarded.

Every field is documented in [SCHEMA.md](SCHEMA.md).

---

## 5. Check that it reproduces

Run the same command again into a different directory and compare. With threads pinned you
should get the same energy to the last digit — that is the guarantee the guard buys you.

You can also re-verify any *published* entry from this repository:

```bash
python scripts/verify_entry.py releases/v4/db/H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_93a0f8a8604d9aed.json
```

Bit-identical energies are guaranteed on the reference pinned environment. Across
*different* machines, what holds is that the entry still certifies — the distinction, and
why it exists, is in [docs/VERIFY.md](docs/VERIFY.md).

---

## 6. Compare against the leaderboard

Every certified entry is public at
**[qencode-benchmark.org/leaderboard](https://www.qencode-benchmark.org/leaderboard)**,
ranked three ways — accuracy, circuit cost, and a balanced score — with a per-entry page
showing the full artifact.

The current suite is **47 certified entries across 16 molecules**, from H₂ up to the H₁₀
chain (20 qubits before tapering).

You can also query it directly:

```bash
curl 'https://www.qencode-benchmark.org/api/leaderboard?category=accuracy&molecule=H2'
```

---

## 7. Try something harder

```bash
# N₂ — a triple bond; needs CASSCF orbitals to partition the active space
qencode run --molecule N2 --mapping jordan_wigner --ansatz-type hardware_efficient \
  --orbital-opt casscf --out-dir out

# ADAPT-VQE — grows the ansatz one operator at a time; the only method
# in the suite that certifies the large hydrogen chains
qencode run --molecule H6 --mapping jordan_wigner --ansatz-type adapt \
  --orbital-opt casscf --out-dir out
```

Larger systems (H₈, H₁₀) use `--adapt-engine statevector --adapt-inner bfgs` and take
hours, not minutes. For those, run under `tmux` or `nohup`; checkpoints are written to
`.ckpt_*.json` after each restart and removed on success.

---

## 8. Check your own VQE setup

The determinism problem QEncode enforces against is not specific to QEncode. If you run VQE
anywhere, this reports whether *your* environment can produce reproducible results:

```bash
python tools/check_vqe_reproducibility.py    # from a clone
qencode check                                # same tool, installed
```

It checks four things — single-threaded BLAS, recorded package versions, a recorded seed,
and a clean code version — and prints the fix for the one that usually fails. It needs only
NumPy and SciPy, and works on any codebase, not just this one.

---

## Troubleshooting

**`pip install` fails building PySCF on Windows.** PySCF has no native Windows wheels. Use
WSL2 + Ubuntu. Scoring (§1) does not need PySCF and works natively.

**The guard refuses to write an entry.** Read which of the three checks failed. Threads is
the one that matters and cannot be bypassed; the other two have `--allow-dirty` and
`--allow-env-drift`, which annotate the run rather than hiding the problem.

**A published entry does not reproduce bit-for-bit on your machine.** Expected for
gradient-free optimisers across machines, and not a fault. Use
`scripts/verify_entry.py --mode certification`, which asserts the property that does hold.
See [docs/VERIFY.md](docs/VERIFY.md).

**`conda: command not found`.** Conda is optional — `pip install qencode-benchmark` into
any Python 3.10+ environment is enough. If you want it, install
[Miniconda](https://docs.conda.io/en/latest/miniconda.html) and restart your shell.

---

## Where to go next

- **[Benchmark specification](https://www.qencode-benchmark.org/benchmark)** — the fixed definitions
- **[Methodology](https://www.qencode-benchmark.org/methodology)** — active spaces, references, metric
- **[Trust policy](docs/TRUST_POLICY.md)** — what *certified* means, and what it does not
- **[Reading the leaderboard](https://www.qencode-benchmark.org/leaderboard/guide)** — every column explained
- **[Why threading breaks VQE](https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug)** — the finding that shaped this suite

Questions, a result you would like listed, or a molecule you think belongs in the suite:
**support@qencode-benchmark.org**. Contributions and issues are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).
