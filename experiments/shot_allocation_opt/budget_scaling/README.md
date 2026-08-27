# Budget scaling curves

> **Consolidated write-up:** [docs/SHOT_NOISE_AND_ALLOCATION.md](../../docs/SHOT_NOISE_AND_ALLOCATION.md) states the ranked practical recommendations from all five studies in one place. This directory is the underlying data.

1600 runs. At what budget does allocation quality start to matter, and what is the
measurement penalty in units of shot budget?

2 molecules x 4 optimisers x 4 schemes x 5 budgets x 10 seeds. Shots per evaluation held
at 1e5 throughout, so total budget maps directly onto evaluation count: 1e6 -> 10
evaluations, 3e6 -> 30, 1e7 -> 100, 3e7 -> 300, 1e8 -> 1000.

The `_r` (refuse-to-stop) forms are the **primary series**. With default stopping the
curve is not a budget curve at all: COBYLA spends 97 to 120 evaluations no matter how
large the budget, so the x-axis stops meaning anything past 1e7. The `_r` variants spend
their full allowance at every point (10/10, 30/30, ... 1000/1000), which is what makes
these curves interpretable.

## Read the success rate, not the median

The per-seed outcome is **bimodal**. A run either catches and converges or stays stuck
near its starting energy; it does not drift smoothly downward as the budget grows. LiH
with L-BFGS-B parameter-shift at 1e8 shots, Neyman allocation, ten seeds:

```
1.5   2.3   2.8   3.5   3.5   4.2   4.8   26.3   176.7   255.9    mHa
```

Seven converged, one nearly, two did not. A median of 3.84 mHa is a true statement about
that set and a misleading summary of it. What actually scales with budget is the
**fraction of runs that converge**, so that is the headline table.

## Success rate: seeds reaching under 10 mHa, out of 10

| molecule / optimiser | scheme | 1e6 | 3e6 | 1e7 | 3e7 | 1e8 |
|---|---|---|---|---|---|---|
| H2O / COBYLA_r | uniform | 0 | 0 | 0 | 0 | 0 |
| | weighted | 0 | 0 | 0 | 0 | 2 |
| | **neyman** | 0 | 0 | 0 | 0 | **2** |
| | *exact* | 0 | 0 | *5* | *10* | *10* |
| LiH / LBFGSB_ps_r | uniform | 0 | 0 | 0 | 0 | 0 |
| | weighted | 0 | 0 | 0 | 0 | 3 |
| | **neyman** | 0 | 0 | 0 | 0 | **7** |
| | *exact* | 0 | 0 | 0 | 0 | *10* |
| H2O / LBFGSB_ps_r | uniform | 0 | 0 | 0 | 0 | 8 |
| | weighted | 0 | 0 | 0 | 1 | 7 |
| | **neyman** | 0 | 0 | 0 | 0 | **9** |
| | *exact* | 0 | 0 | 0 | 1 | *9* |

Three things fall out.

**Below 1e8 shots nothing works under sampling noise.** Every scheme, every optimiser,
0/10 at 1e6 through 3e7. Allocation quality is irrelevant in that whole range — not
because it fails, but because no scheme succeeds. The crossover where paying for variance
estimation starts to buy anything is at or above 1e8 shots for these systems.

**The measurement penalty is worth more than 30x in budget.** H2O with COBYLA reaches
10/10 on exact arithmetic at 3e7 shots. The best noisy scheme manages 2/10 at 1e8 — more
than three times the budget, for a fifth of the success rate. Better allocation recovers
part of that penalty; it does not come close to removing it.

**Where allocation does matter, it matters a lot.** LiH with parameter-shift gradients at
1e8: uniform 0/10, weighted 3/10, Neyman 7/10, exact 10/10. That is the single clearest
result in this directory, and it is the same cell that showed 27x on medians in the parent
study.

And one negative: on H2O with parameter-shift, uniform already reaches 8/10 and Neyman
adds one seed. That matches the early-stopping control, which found the pilot actively
counterproductive in that cell.

## Median gaps, for completeness

LiH / LBFGSB_ps_r, median over 10 seeds, mHa:

| total budget | uniform | weighted | neyman | exact | neyman/uniform |
|---|---|---|---|---|---|
| 1e6 (10 ev) | 518.85 | 520.34 | 514.24 | 514.24 | 1.01x |
| 3e6 (30 ev) | 424.94 | 419.94 | 420.25 | 416.86 | 1.01x |
| 1e7 (100 ev) | 411.91 | 408.03 | 409.00 | 406.24 | 1.01x |
| 3e7 (300 ev) | 413.83 | 396.08 | 391.61 | 322.26 | 1.06x |
| 1e8 (1000 ev) | 398.93 | 155.90 | **3.84** | 0.16 | **104x** |

H2O / COBYLA_r:

| total budget | uniform | weighted | neyman | exact | neyman/uniform |
|---|---|---|---|---|---|
| 1e6 | 1010.63 | 1010.92 | 1002.11 | 998.36 | 1.01x |
| 3e6 | 991.48 | 971.05 | 960.87 | 803.65 | 1.03x |
| 1e7 | 982.82 | 974.19 | 952.69 | 10.91 | 1.03x |
| 3e7 | 968.39 | 942.43 | 887.92 | 0.40 | 1.09x |
| 1e8 | 586.55 | 24.93 | **17.55** | 0.40 | **33x** |

The shape is the same in both: flat at ~1.0x across four budget decades, then a jump of
one to two orders of magnitude in the last step. This is not a gentle crossover that could
be interpolated — nothing in the first four points predicts the fifth.

## What is limiting, by budget

Share of the exact-arithmetic ceiling still unclosed by Neyman, `(neyman - exact)/neyman`:

| molecule / optimiser | 1e6 | 3e6 | 1e7 | 3e7 | 1e8 |
|---|---|---|---|---|---|
| H2O / COBYLA_r | 0% | 16% | 99% | 100% | 98% |
| LiH / COBYLA_r | 0% | 2% | 57% | 91% | 100% |
| LiH / LBFGSB_ps_r | 0% | 1% | 1% | 18% | 96% |
| H2O / LBFGSB_ps_r | 0% | 0% | -1% | -0% | 93% |

At the smallest budgets the noisy runs match exact arithmetic — measurement is free
because the optimiser has too few evaluations to exploit a cleaner signal anyway. The
regime flips as budget grows: by 1e8 essentially the entire remaining gap is measurement.

So the two constraints hand off rather than overlapping. Evaluations bind first;
measurement binds later; and the budget where allocation quality starts to pay is the
budget where that handoff completes.

## Caveats

- Two molecules, four optimisers, one shots-per-evaluation setting (1e5). The orthogonal
  sweep — fixing evaluations and varying noise per evaluation — is not run here.
- The curve stops at 1e8 shots. Several cells are still climbing there, so these are
  lower bounds on what more budget would give, and the crossover is bracketed as "at or
  above 1e8", not located.
- Ten seeds per cell. With a bimodal outcome that resolves a success rate to about one
  decimal place and no better; 2/10 versus 3/10 is not a distinction this supports.
- L-BFGS-B with finite-difference gradients is excluded: the early-stopping control found
  it unrescuable at any allocation or stopping rule, so it would contribute five flat
  lines.
- Statevector throughout, no gate or readout noise.

## Reproducing

```bash
SPSA_A=5.0 SPSA_C=0.1 python tools/shot_allocation_optimize.py LiH LBFGSB_ps_r neyman 100000000 100000 0 out/
python tools/analyse_budget_scaling.py out/
```
