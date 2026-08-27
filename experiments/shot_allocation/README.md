# Shot allocation for VQE energy estimation

Measurement of how a fixed shot budget should be split across the Pauli terms of a
molecular Hamiltonian, and what goes wrong with the textbook answer.

270 runs: 10 molecules (20 to 919 Pauli terms) x 3 parameter states x 3 shot budgets,
each scheme repeated 200 times to measure its error distribution.

## The question

A VQE energy is a weighted sum over Pauli terms, `E = sum_i c_i <P_i>`. Each `<P_i>`
has to be sampled. Given a total budget of `N` shots, how many should each term get?

Three answers, all charged the *same* total budget:

| scheme | allocation | note |
|---|---|---|
| `uniform` | `s_i = N / L` | what most VQE code does by default |
| `weighted` | `s_i ~ \|c_i\|` | weighted random sampling, as in Rosalin |
| Neyman | `s_i ~ \|c_i\| sigma_i` | the variance-minimising split |

Neyman allocation is the textbook optimum for a weighted sum of independent estimators,
and it is the right answer here in principle: term variances are wildly unequal, because
a Pauli string that is close to an eigenoperator of the current state has `sigma_i` near
zero, and shots spent on it buy nothing. Weighting by `|c_i|` alone cannot see that.

## The finding

**Neyman allocation with a pilot-estimated sigma is catastrophically biased**, and the
bias is invisible if you only look at the spread of the estimator.

`sigma_hat_i = sqrt(1 - m^2)` from a pilot of `per` shots is **exactly zero** whenever the
pilot draw comes out all-heads or all-tails. For a near-deterministic term that is likely.
The term is then allocated zero shots and silently dropped from the energy sum.

And near-deterministic Pauli strings tend to carry *large* coefficients. So the rule
preferentially discards the terms that matter most:

- terms killed this way carry **9.1x the mean `|c_i|`** of the terms kept
- a median of **48% of `lambda = sum |c_i|`** is dropped
- median RMSE **604 mHa**, against **11.4 mHa** for plain uniform allocation

It beats uniform in only 22 of 90 runs. Judged on standard deviation alone it looks like
the best scheme in the study — its spread really is the smallest. It is simply centred in
the wrong place.

## The fix

Two independent repairs, both cheap:

1. **Shrink the variance estimate.** Use the Agresti-Coull proportion
   `p = (k + 1) / (per + 2)`, which is never exactly 0 or 1, so `sigma_hat` is never
   exactly zero and no term is ever starved. Add a floor of one shot per live term.
2. **Pool the pilot with the main pass.** The pilot is already paid for. Combine the two
   samples per term, shot-weighted, instead of throwing the pilot away.

Together (`best` in the results) this recovers the whole gain:

| scheme | median RMSE | vs uniform | beats uniform |
|---|---|---|---|
| `uniform` | 11.35 mHa | 1.00x | — |
| `weighted` | 9.68 mHa | 1.17x | 58/90 |
| `naive` Neyman | 603.70 mHa | 0.04x | 22/90 |
| `shrunk` | 8.88 mHa | 1.45x | 81/90 |
| `best` | 8.49 mHa | **1.53x** | **84/90** |
| `oracle` (exact sigma) | 7.41 mHa | 1.69x | 86/90 |

Because variance falls as `1/N`, a 1.53x cut in RMSE is **2.33x fewer shots** for the same
accuracy. The pilot costs only 6% above the oracle ceiling.

The gain is consistent — it does not depend on cherry-picking a molecule or a state:

| | median | range |
|---|---|---|
| by state: start / mid / converged | 1.46x / 2.07x / 1.32x | 0.83-3.26x |
| by budget: 1e4 / 1e5 / 1e6 | 1.44x / 1.50x / 1.63x | |
| by molecule (all 10) | 1.25x to 1.99x | |

## Correction to an earlier number

A preliminary version of this measurement reported **8.9x** on LiH. That number was wrong
in three ways, all of which this study was designed to catch:

- it was measured at a **random starting point**, not where an optimiser actually works —
  the same molecule gives 2.0x once converged;
- it compared **standard deviation only**, so the bias described above did not appear;
- it rested on **two molecules and one parameter point**.

The validated figure is ~1.5x in RMSE, ~2.3x in shots.

## Reproducing

```bash
python tools/shot_allocation.py <molecule> <state> <budget> <outdir>
python tools/analyse_shot_allocation.py <outdir>
```

`state` is `start`, `mid`, or `converged`; the parameters for each are found by exact
statevector optimisation, so no sampling enters the choice of state.

`experiments/shot_allocation/run_grid.sh` runs the full 90-job grid. Every job is
single-threaded (`OMP_NUM_THREADS=1` and friends pinned before numpy is imported, as
everywhere in this repository) and parallelism is across jobs only.

## A note on the sampling model

Terms are drawn from `Binomial(s, (1 + <P>)/2)` rather than by executing the circuit `s`
times. A Pauli observable has +-1 eigenvalues, so this is the exact sampling distribution,
not an approximation — which is what makes 200 repeats across 919 terms affordable.

That claim is tested rather than asserted: `binomial_check.py` runs both paths on the same
state and allocation. Agreement is within sampling noise (ratios 1.026 and 0.950 against a
+-0.196 band at 200 repeats).

## Scope

- Shots are counted **per term**, so the total is exactly `sum(s_i)`. Commuting-group
  measurement is an orthogonal saving and composes with any of these schemes; it is not
  modelled here, and no claim in this directory depends on it.
- This measures the **energy estimator**, not a full optimisation run. Whether the RMSE
  reduction converts into faster or more reliable VQE convergence is a separate question
  and is not answered here.
- Statevector simulation throughout. No gate noise, no readout error, no device topology.

## Layout

```
v1_std_only/   first grid, judged on standard deviation -- where the bias hid
v2_fixes/      the repairs, judged on RMSE
final/         the full scheme set including `best`
*.log          raw cluster logs for all three grids
```
