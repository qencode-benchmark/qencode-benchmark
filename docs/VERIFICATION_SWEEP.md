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
