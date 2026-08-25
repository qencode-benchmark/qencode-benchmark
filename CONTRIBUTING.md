# Contributing to QEncode

Thanks for looking. QEncode is a benchmark, so the bar for a contribution is not
"does it work" but **"can someone else get the same number."** Everything below
follows from that.

By contributing you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE).

---

## The rules that are not negotiable

These are what the project exists to enforce. A change that weakens them will not be
merged, however convenient it is.

**1. A result is never adjusted, discarded, or re-rolled.**
If a configuration fails to reach the 10 mHartree threshold, that is a result. It is
recorded as *research tier* and published. We do not re-run until a number looks
better, and we do not quietly drop entries that disappoint. If you find yourself
wanting to, that is exactly the case the benchmark exists to capture.

**2. Determinism is enforced, not assumed.**
Every entry is generated with the linear-algebra backend pinned to a single thread,
package versions matching `requirements-v4.txt`, and a clean git tree. The guard in
`scripts/generate_entry_v4.py` refuses to write an entry otherwise. This is not
bureaucracy — multi-threaded BLAS made our own published numbers irreproducible, and
[we had to retract one](https://www.qencode-benchmark.org/blog/vqe-reproducibility-threading-bug).

**3. Every number comes from the pipeline.**
No hand-edited energies, no numbers copied from a paper into an entry. If it is in an
entry file, the pipeline produced it and re-running reproduces it.

---

## Getting set up

```bash
git clone https://github.com/qencode-benchmark/qencode-benchmark
cd qencode-benchmark

# Option A — Docker: the pinned environment, determinism already enforced
docker build -t qencode .

# Option B — local (Python 3.11; PySCF does not build natively on Windows)
pip install -r requirements-v4.txt
pip install -r requirements-tools.txt   # only for the leaderboard scripts
```

Confirm your machine can produce reproducible results at all:

```bash
python tools/check_vqe_reproducibility.py
```

Then reproduce a published entry before changing anything — it is the fastest way to
know your environment is sane:

```bash
python scripts/verify_entry.py releases/v4/db/H2_ccpvdz_JW_UCCSD_v4_tapered__sha256_93a0f8a8604d9aed.json
```

---

## Ways to contribute

### Report a result that does not reproduce

The most valuable thing you can send us. Open an issue with the entry ID, the command
you ran, and the output of `tools/check_vqe_reproducibility.py` on your machine. We
would rather hear it from you than not know.

### Propose a molecule

Molecules live in `molecules_v4.json`. A good candidate has a chemical reason to be
there — a correlation regime, symmetry, or bonding situation the suite does not
already cover — not just a larger qubit count. Open an issue first describing:

- geometry and its source (published structure, optimised at what level)
- the active space `[n_electrons, n_orbitals]` and why that partition is the chemically
  meaningful one
- whether HF orbitals separate the active space or CASSCF is required
- roughly what it costs to run

Geometry correctness matters more than anything else here; a wrong bond length makes
every entry for that molecule meaningless.

### Submit a benchmark entry

See [docs/SUBMISSIONS.md](docs/SUBMISSIONS.md). In short: run the pipeline unmodified,
keep the guard satisfied, and send the entry JSON. Entries carry a SHA-256 content
hash, so a modified entry will not validate.

### Change the pipeline

Any change that could move a published number must say so explicitly in the pull
request, and the affected entries have to be regenerated in the same change. A commit
that silently shifts results is worse than no commit — the suite's value is that a
number and its provenance agree.

---

## Pull requests

- Branch from `master`, keep the change focused.
- Explain **why** in the commit message, not just what. The reasoning is what a future
  reader needs; the diff already shows the change.
- If you fixed a bug, say what it silently did wrong and how you know it is fixed.
- Run the scripts you touched. `--help` at minimum; a real entry if you changed the
  pipeline.
- Do not commit bytecode, entry files you generated while testing, or anything under
  `releases/` unless the entries are the point of the PR.

---

## Questions

Open an issue, or email **support@qencode-benchmark.org**. If you are using QEncode in
research and something is unclear or wrong, we would genuinely like to know — a
benchmark nobody can question is not doing its job.
