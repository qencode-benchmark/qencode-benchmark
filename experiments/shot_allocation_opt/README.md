# Does better shot allocation change the OUTCOME of a VQE optimisation?

The companion study in `experiments/shot_allocation/` showed that Neyman allocation with
shrinkage and pooling cuts energy RMSE ~1.5x at equal cost. That is a statement about the
estimator in isolation. This asks the question that actually matters for anyone running
VQE: does feeding an optimiser the cleaner signal change where it ends up?

1200 runs: 2 molecules x 5 optimisers x 4 allocation schemes x 3 budgets x 10 seeds.

## The target

The archived failure in `experiments/v3_hf/`: LiH, L-BFGS-B, 1000 shots per commuting
group, budget 100 evaluations. All ten seeds land between 685 and 710 mHa. The tightness
of that clustering is itself a clue — a noise-driven failure would scatter.

## The short answer

**At the budget where the collapse happened, no.** Better allocation moves LiH/L-BFGS-B
by 0.7 mHa out of 707. The collapse was never mostly a measurement problem.

**At a 10x larger evaluation budget, yes, and substantially** — up to 27x — but through a
mechanism that was not the expected one. Not "cleaner signal, better gradient steps", but
**"cleaner signal, the optimiser stops quitting early"**.

## What separates the two explanations

Two things were confounded in the original failure, so the budget axis carries three
points that pull them apart:

| | total shots | per evaluation | evaluations | tests |
|---|---|---|---|---|
| A | 1e7 | 1e5 | 100 | replicates the original scale |
| B | 1e8 | 1e5 | 1000 | 10x the steps, same noise |
| C | 1e8 | 1e6 | 100 | same steps, 10x cleaner |

Plus an `exact` control at every budget: the identical optimiser with sampling switched
off entirely, capped at the same evaluation count. **A noisy run that matches its exact
control was never limited by measurement**, and no allocation scheme can help it.

## Result 1: the collapse was budget starvation, not measurement

LiH, L-BFGS-B, budget A. All schemes use exactly 100 evaluations and 9.99M shots, so this
comparison is matched to within 0.03%:

| scheme | median gap | evals | shots |
|---|---|---|---|
| uniform | 707.85 mHa | 100 | 9,994,600 |
| weighted | 708.42 mHa | 100 | 9,990,800 |
| neyman | 707.19 mHa | 100 | 9,992,354 |
| **exact arithmetic** | **651.67 mHa** | 100 | 0 |

With *perfect* arithmetic and the same 100 evaluations the optimiser still fails at
651.67 mHa. Sampling noise accounts for 56 mHa of the 707; the remaining 92% is simply
too few evaluations. Neyman allocation recovers 0.7 mHa of that 56.

For reference, with enough exact evaluations every optimiser here solves LiH to well
under 1 mHa (L-BFGS-B: 0.03 mHa in 864 evaluations). The molecule is not hard. The budget
was.

## Result 2: where noise does bite, it bites through premature termination

Give the optimisers 1000 evaluations and the interesting thing is not the energy, it is
how many evaluations they actually spend before their own convergence test fires:

| optimiser | uniform | weighted | neyman | exact |
|---|---|---|---|---|
| COBYLA | 120 | 116 | 126 | 1000 |
| L-BFGS-B (finite diff) | 400 | 408 | 416 | 744 |
| L-BFGS-B (param-shift) | 310 | 372 | **822** | 1000 |
| Adam | 1000 | 1000 | 1000 | 1000 |
| SPSA | 1000 | 1000 | 1000 | 1000 |

Every optimiser with a convergence test mistakes sampling noise for convergence and quits
early — COBYLA burns 120 of 1000 evaluations and declares itself done. Adam and SPSA have
no such test and always spend the budget.

This is what a better estimator actually buys: it delays the false convergence signal.

## Result 3: the largest effect, and its honest accounting

LiH, L-BFGS-B with parameter-shift gradients, budget B:

| scheme | median gap | evals used | shots consumed | of 1e8 budget |
|---|---|---|---|---|
| uniform | 408.97 mHa | 310 | 31.0M | 31% |
| weighted | 396.08 mHa | 372 | 37.2M | 37% |
| **neyman** | **14.88 mHa** | 822 | 82.1M | 82% |
| exact | 0.16 mHa | 1000 | 0 | — |

A 27x improvement — but the shot counts must be read alongside it. Both schemes were
*offered* 1e8 shots. Uniform could only spend 31% of it before stalling. So this is not
"the same shots spent better", it is **the cleaner estimator converting unspendable
budget into spendable budget**. That distinction matters and is easy to lose.

## Result 4: clean equal-shot comparisons

Adam and SPSA never terminate early, so their shot counts match to within 0.02% and no
interpretation is needed:

| molecule | optimiser | uniform | weighted | neyman | exact |
|---|---|---|---|---|---|
| LiH | SPSA | 155.90 | **31.80** | 54.46 | 11.33 |
| LiH | Adam | 93.34 | 49.65 | 61.41 | 63.19 |
| H2O | SPSA | 9.24 | 5.55 | **5.14** | 2.14 |
| H2O | Adam | 182.63 | 177.56 | 179.27 | 182.46 |

Real gains of 1.5x to 4.9x. Note that plain `|c_i|` weighting beats Neyman on LiH/SPSA —
the estimator study found Neyman better *on average*, not universally, and that shows up
here.

Also matched, and the largest clean win in the study — H2O, COBYLA, budget C (100
evaluations at 1e6 shots each): uniform 370.88 mHa, neyman **20.69 mHa**, exact 10.91.

## Overall

Across all 30 (molecule, optimiser, budget) cells, Neyman beats uniform by more than
1 mHa in 19, loses by more than 1 mHa in 5, and ties in 6.

Both scoring metrics agree in direction in every cell checked — `gap_best` (exact energy
at the parameters whose *noisy* estimate was lowest, which is what a practitioner would
actually return) and `gap_final` (exact energy at the last point). Both are recorded.

## SPSA

SPSA was untested in earlier work, so it is included here. It required calibration before
any noisy run could be believed: with textbook-default gains it **never moved at all**,
sitting at 722 mHa after 5000 exact-arithmetic evaluations. A sweep at zero noise over
a in {0.5 ... 20} and c in {0.05, 0.1, 0.2} (`spsa_calibration/`) picked a = 5.0, c = 0.1,
which reaches 1.97 mHa. That is the configuration used throughout.

Its real advantage is not noise-robustness in the usual sense. It is that SPSA has no
convergence test to trip, so it always spends its budget, and it costs 2 evaluations per
iteration regardless of parameter count while parameter-shift costs 2N.

## Scope and caveats

- **This is a reconstruction at matched scale, not a bit-identical replay** of the
  archived runs. Those used PennyLane grouped-Hamiltonian measurement; this counts shots
  per term so the accounting is exact. The archived L-BFGS-B stopped at 14 evaluations;
  here it runs to the cap. The qualitative failure reproduces, the trajectory does not.
- Sampling uses `Binomial(s, (1+<P>)/2)`, the exact distribution for a +-1 observable,
  validated against circuit execution in `../shot_allocation/binomial_check.py`.
- Statevector throughout. No gate noise, no readout error, no device topology.
- Two molecules. LiH is the archived failure; H2O is a control. Nothing here establishes
  how this behaves at 20 qubits.
- `spsa_calibration/` records were produced before a fix to final-parameter tracking, so
  their `gap_final` field is unreliable. The ranking used `gap_best`, which is unaffected.

## Reproducing

```bash
SPSA_A=5.0 SPSA_C=0.1 python tools/shot_allocation_optimize.py LiH LBFGSB_ps neyman 100000000 100000 0 out/
python tools/analyse_shot_allocation_optimize.py out/
```

Arguments: molecule, optimiser, scheme, total shot budget, shots per evaluation, seed,
output directory. `scheme` is `uniform`, `weighted`, `neyman`, or `exact`.
