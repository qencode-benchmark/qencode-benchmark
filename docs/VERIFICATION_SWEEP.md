# Verifying the whole database

**Status: 52 of 54 entries complete.** H₁₀ (ADAPT, 20 qubits) and H₆ (HEA, CASSCF) are
still running. Headline numbers below are provisional and will be updated when they land.

QEncode's central claim is that any published result can be independently rebuilt. Until
now that claim had never been tested across the database, and it could not have been:
`scripts/verify_entry.py` **could not re-run 29 of the 54 entries at all**, and failed
another 3 for a second reason. Both faults were in the verifier, not in the results.

This is the first end-to-end check, run from a clean checkout in the pinned environment
with no override flags. Each entry is a complete VQE re-run compared against its stored
energy at 10⁻⁶ Ha.

Data: `experiments/verification_sweep/`. Tools: `tools/verify_sweep.sh`,
`tools/analyse_verification_sweep.py`.

---

## Two bugs, both in the checking rather than the results

### 1. The verifier could not run 29 of 54 entries

Entries record the ansatz in the pipeline's *internal* vocabulary, which is not its
*command line* vocabulary. 29 entries store `ansatz_type: "hea"`; `--ansatz-type` accepts
only `uccsd`, `hardware_efficient` and `adapt`. Every one of those verifications died at
the first call:

```
generate_entry_v4.py: error: argument --ansatz-type: invalid choice: 'hea'
```

The existing code mapped `uccsd_tapered` → `uccsd` with a `.replace()`, so UCCSD and ADAPT
entries were fine. `hea` was simply never mapped. Fixed in `a298c51` with an explicit
vocabulary table rather than another string operation, so the next divergence is visible
rather than silent.

**This is why the claim had never been tested.** More than half the database could not be
checked, and the failure looked like a configuration error rather than a reproducibility
problem.

### 2. The verifier re-ran 3 entries at the wrong iteration budget

Of the entries that could now run, three failed with energy differences up to 221 mHa. The
cause separates perfectly on one field:

| recorded `max_iterations` | entries | reproduced |
|---|---|---|
| **500** (the generator default) | 46 | **46 — 100%** |
| 1000 | 2 | **0** |
| 10000 | 1 | **0** |

`grep -c "max-iter" scripts/verify_entry.py` returned **0**. The verifier never passed the
recorded iteration cap, so any entry needing more than the default 500 was silently re-run
at 500 and landed on a different result. Fixed by passing `run_config.max_iterations`
through.

Confirmed: H₄, which failed at 8.97 × 10⁻⁴ Ha, now reports
`PASS — VQE energy reproduced` in 58 seconds. N₂ and benzene are re-running.

### 3. A usability gap found while fixing the first two

The verifier offered no way to pass `--allow-dirty` or `--allow-env-drift` through to the
generator. The reproducibility guard correctly refuses to *write* an entry from a dirty
tree or a drifted environment — but that same refusal made **verification impossible for
anyone whose machine is not byte-identical to ours**, which is everyone checking our work
from outside, and the only audience the tool has. Both flags now pass through.

---

## Results so far

| | |
|---|---|
| entries swept | 52 of 54 |
| reproduced | **49 (94.2%)** |
| failed | 3 — all from the `max_iterations` bug, all being retested |
| shown irreproducible | **0** |

By ansatz, with the `hea` rows being the ones that could not be run at all before `a298c51`:

| ansatz | entries | reproduced |
|---|---|---|
| `adapt` | 9 | 9 |
| `hea` | 25 | 24 |
| `uccsd_tapered` | 15 | 13 |

**No entry has been shown to be irreproducible.** Every failure so far traces to the
verifier not faithfully reconstructing the configuration the entry records.

---

## What this exercise says

The results were fine. The tool that checks them was not, in two separate ways, and one of
those made the check impossible for a majority of the database.

That is worth stating plainly because the failure mode is instructive: a verifier that
errors out looks like a broken command, not like a broken guarantee. Nobody had run it
across everything, so nobody had seen that it could not. A benchmark whose value rests on
independent reproducibility needs its verifier exercised over the whole database, not
spot-checked — and needs that in CI rather than by hand.

---

## Reproducing

```bash
bash tools/verify_sweep.sh                                   # the full sweep
python tools/analyse_verification_sweep.py <records dir>     # the summary
python scripts/verify_entry.py <entry.json>                  # one entry
```

Each job is single-threaded with parallelism across entries only — the same isolation rule
the rest of the suite uses, so no run perturbs another's arithmetic. Failures are recorded
as failures and nothing is retried with overrides.

## Caveats

- **Two entries outstanding.** H₁₀ and H₆ are the two heaviest in the suite and were still
  running when this was written. Their results will change the counts above.
- Verification compares the **energy** to 10⁻⁶ Ha and checks the stored hash. It does not
  re-derive every recorded field.
- Run on one machine and one pinned environment. Reproducibility across *different*
  machines is a separate question, and the backend probe in
  [`DEFERRED_TRACKS_FEASIBILITY.md`](DEFERRED_TRACKS_FEASIBILITY.md) shows why it is not
  automatic for gradient-free optimisers.
