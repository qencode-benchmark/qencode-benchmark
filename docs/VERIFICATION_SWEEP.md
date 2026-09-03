# Verifying the whole database

**All 54 published entries reproduce.** 51 on the first pass; the other 3 failed because
of a bug in the verifier, and reproduce once it is fixed.

QEncode's central claim is that any published result can be independently rebuilt. Until
this sweep that claim had never been tested across the database — and it could not have
been, because `scripts/verify_entry.py` **could not re-run 29 of the 54 entries at all**.
Three faults were found. All three were in the verifier. **None were in the results.**

Run from a clean checkout in the pinned environment with no override flags. Each entry is
a complete VQE re-run compared against its stored energy at 10⁻⁶ Ha, with the stored hash
checked for tampering. 8.0 hours of compute; median entry 24 s, slowest 2.1 hours.

Data: `experiments/verification_sweep/`. Tools: `tools/verify_sweep.sh`,
`tools/analyse_verification_sweep.py`.

---

## Result

| | |
|---|---|
| entries | **54 of 54** |
| reproduced on the first pass | 51 |
| reproduced after fixing the verifier | **54 — all of them** |
| shown irreproducible | **0** |
| hash mismatches | **0** |

By ansatz. The `hea` row is the 29 entries the verifier could not run at all before this:

| ansatz | entries | reproduced |
|---|---|---|
| `adapt` | 10 | 10 |
| `hea` | 29 | 29 |
| `uccsd_tapered` | 15 | 15 |

The two largest systems, which are also the two slowest to verify, both reproduce:
**H₆ (HEA/CASSCF) in 2.1 hours** and **H₁₀ (ADAPT, 20 qubits before tapering) in 2.0 hours**.

---

## The three faults, all in the checking

### 1. The verifier could not run 29 of 54 entries

Entries record the ansatz in the pipeline's *internal* vocabulary, which is not its
*command line* vocabulary. 29 entries store `ansatz_type: "hea"`; `--ansatz-type` accepts
only `uccsd`, `hardware_efficient` and `adapt`. Every one of those verifications died at
the first call:

```
generate_entry_v4.py: error: argument --ansatz-type: invalid choice: 'hea'
```

`uccsd_tapered` → `uccsd` was already handled by a `.replace()`. `hea` was simply never
mapped. Fixed in `a298c51` with an explicit vocabulary table, so the next divergence is
visible rather than silent.

**This is why the claim had never been tested.** More than half the database could not be
checked, and the failure looked like a configuration error rather than a broken guarantee.

### 2. Three entries were re-run at the wrong iteration budget

Of the entries that could then run, three failed with energy differences up to 221 mHa.
The cause separates perfectly on one field:

| recorded `max_iterations` | entries | reproduced |
|---|---|---|
| **500** (the generator default) | 51 | **51 — 100%** |
| 1000 | 2 | 0 |
| 10000 | 1 | 0 |

`grep -c "max-iter" scripts/verify_entry.py` returned **0**. The verifier never passed the
recorded cap, so any entry needing more than 500 iterations was silently re-run at 500 and
landed on a different result. Fixed in `0d20bd0` by passing `run_config.max_iterations`
through.

All three then reproduce:

| entry | before | after |
|---|---|---|
| H₄ / JW / UCCSD | FAIL, 8.97 × 10⁻⁴ Ha | **PASS** in 58 s |
| N₂ / JW / UCCSD / CASSCF | FAIL, 1.28 × 10⁻¹ Ha | **PASS** in 2.1 h |
| benzene / JW / HEA / CASSCF | FAIL, 2.21 × 10⁻¹ Ha | **PASS** in 35 min |

### 3. The verifier was unusable on any machine but ours

It offered no way to pass `--allow-dirty` or `--allow-env-drift` through to the generator.
The guard correctly refuses to *write* an entry from a dirty tree or a drifted environment
— but that same refusal made **verification impossible for anyone whose machine is not
byte-identical to ours**, which is everyone checking our work from outside, and the only
audience the tool has. Both flags now pass through.

---

## What this says

The results were sound. The tool that checks them was not, in three separate ways, and one
of those made checking impossible for a majority of the database.

The failure mode is the instructive part: **a verifier that errors out looks like a broken
command, not a broken guarantee.** Nobody had run it across everything, so nobody had seen
that it could not. A benchmark whose value rests on independent reproducibility needs its
verifier exercised over the whole database, and needs that automatically.

It now is — see `.github/workflows/ci.yml`:

- **every push and pull request** replays a six-entry subset chosen to include a regression
  test for each bug above, about a minute of compute
- **every Sunday** replays 40 of the 54 entries, sharded four ways

The other 14 are the CASSCF and ADAPT runs on N₂, H₆, H₈, H₁₀ and benzene, at 5 minutes to
2.1 hours each. They do not fit a 6-hour CI job and are verified on the cluster instead;
`.github/verify_ci_entries.txt` names each one with its measured time and the reason.

---

## Across machines: what actually holds

The sweep above ran on the reference pinned environment. The weekly CI job runs on GitHub
runners, and its first execution (2026-08-30) failed all four shards — because it asserted
bit-level energy agreement, which the numerics do not support across machines.

Re-running 39 entries on an environment with drifted package versions:

| | energy movement |
|---|---|
| median | 7.7 × 10⁻⁸ Ha |
| 90th percentile | 2.1 × 10⁻³ Ha |
| maximum | 1.4 × 10⁻² Ha |

**17 of 39 exceeded the 10⁻⁶ Ha strict tolerance while still certifying.** That is the gap
between "the energy is identical" and "the entry is still valid", and only the second is a
cross-machine property. See the dated amendment in
[`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md).

`scripts/verify_entry.py` now has two modes:

- `--mode strict` (default) — the energy must match to `--tolerance`. This is the
  determinism guarantee, valid on the reference pinned environment. Used by
  `tools/verify_sweep.sh`.
- `--mode certification` — the regenerated entry must still meet the 10 mHa threshold.
  Energy movement is reported but not gated on. Used by the weekly CI job.

### Two entries do not re-certify across environments

| entry | published gap | regenerated gap |
|---|---|---|
| `C4H4_ccpvdz_PAR_HEA` | 6.1 mHa | **20.5 mHa** |
| `C4H4_ccpvdz_JW_HEA` | 9.6 mHa | **19.0 mHa** |

Both were certified close to the 10 mHa threshold, and **an entry certified close to the
threshold is not robustly certified** — a different environment moves it across. This is a
property of those two entries rather than of the verifier, and it is recorded rather than
worked around. Both still reproduce exactly on the reference environment.

A caveat on the measurement: the drifted environment used here has different *package
versions* (pyscf 2.5.0 against the pinned 2.6.2, scipy 1.17 against 1.13.1), a larger
perturbation than CI experiences — CI installs the pins and differs only in Python patch
level and CPU. These figures are an upper bound on what CI sees, not a prediction of it.

### The measurement was not contaminated by threading

It was run five jobs at a time, which raises the obvious objection: the whole reason this
project pins `OMP_NUM_THREADS=1` is that threaded BLAS makes a gradient-free optimiser
non-deterministic, so a measurement of *environment* drift taken under concurrency could
be measuring *thread* drift instead. Checked rather than assumed:

- `QENCODE_ALLOW_THREADS` was never set, so the pipeline pinned threads before importing
  NumPy in every subprocess, and the guard verifying `OMP_NUM_THREADS=1` afterwards
  **cannot be bypassed** by `--allow-dirty` or `--allow-env-drift` — only tree-dirtiness
  can.
- Two entries were measured under different concurrency and agree exactly:

  | entry | in the parallel sweep | re-run separately |
  |---|---|---|
  | `LiH_ccpvdz_JW_HEA` | 1.329 × 10⁻⁴ Ha | 1.329 × 10⁻⁴ Ha |
  | `C4H4_ccpvdz_PAR_HEA` | 1.443 × 10⁻² Ha | 1.443 × 10⁻² Ha |

The second re-run happened to overlap three other jobs and still reproduced bit-identically,
which is stronger than a quiet-machine control: the result does not depend on machine load.
Each job is single-threaded and parallelism is across processes only — the same isolation
rule the rest of the suite uses.

### A stricter gradient-based job is not possible here

Gradient-based optimisers are effectively immune to this amplification, so a strict job
restricted to them would be sound. It cannot be built: **all seven gradient-based entries
are the heavy CASSCF and large-system runs** — H₆, H₈, H₁₀, N₂ ×3 and benzene — at 20
minutes to 2.1 hours each, none of which fits a CI budget. The methods immune to the
problem were used on precisely the systems too expensive to check often.

---

## Reproducing

```bash
bash tools/verify_sweep.sh                                   # the full sweep
python tools/analyse_verification_sweep.py <records dir>     # the summary
python scripts/verify_entry.py <entry.json>                  # one entry
```

Each job is single-threaded with parallelism across entries only — the same isolation rule
the rest of the suite uses, so no run perturbs another's arithmetic. Failures are recorded
as failures and nothing is retried with overrides. The records in
`experiments/verification_sweep/records/` are the **original** sweep, including the three
failures; the post-fix retest is in `retest_logs/` and `retest_after_maxiter_fix.log`. The
history is kept rather than overwritten.

## Caveats

- Verification compares the **energy** to 10⁻⁶ Ha and checks the stored hash. It does not
  re-derive every recorded field.
- Run on one machine and one pinned environment. Reproducibility across *different*
  machines is a separate question, and the backend probe in
  [`DEFERRED_TRACKS_FEASIBILITY.md`](DEFERRED_TRACKS_FEASIBILITY.md) shows it is not
  automatic for gradient-free optimisers — two simulator backends agreeing to 10⁻¹³ Ha on
  arithmetic can still land 11 mHa apart after COBYLA.
