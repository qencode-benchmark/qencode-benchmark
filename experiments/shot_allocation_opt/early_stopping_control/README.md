# Early-stopping control

480 runs. The control for the claim made in the parent directory.

## Why this had to be run

The parent study found that at a 1e8-shot budget, Neyman allocation took LiH with
L-BFGS-B and parameter-shift gradients from 408.97 mHa to 14.88 mHa, and that the
mechanism was **premature termination**: uniform allocation spent 310 evaluations before
its convergence test fired, Neyman spent 822.

If the benefit is really about termination, then simply **refusing to stop** should
recover most of it — and that costs nothing. No pilot pass, no variance estimation, no
10% overhead. If so, the honest recommendation to a practitioner is "do not let a noisy
value trip your convergence test", and "use Neyman allocation" has to be demoted.

That is a cheap experiment and it could invalidate the parent claim, so it goes first.

## What `_r` does

Two things, because L-BFGS-B exits for two different reasons:

- sets the convergence tolerances to zero (`ftol=0, gtol=0`; COBYLA `tol=1e-14`) so the
  optimiser cannot declare itself converged, and
- restarts it from its own final point whenever it returns anyway — L-BFGS-B also exits
  on line-search failure, which no tolerance controls.

It loops until the shot budget is gone. Every `_r` run spends all 1000 evaluations and
99.9M of its 100M budget, in 2 to 4 restarts, so the control demonstrably did its job.

## The answer: no, and the hypothesis was wrong

Median gap over 10 seeds, mHa. Budget 1e8 shots, 1e5 per evaluation, 1000-evaluation cap.

| molecule | optimiser | uniform / default | uniform / nostop | neyman / default | neyman / nostop | |
|---|---|---|---|---|---|---|
| H2O | COBYLA | 982.82 | 586.55 | 952.70 | **17.55** | both needed |
| H2O | L-BFGS-B (finite diff) | 1060.49 | 1052.21 | 1062.70 | 1052.22 | nothing helps |
| H2O | L-BFGS-B (param-shift) | 15.79 | **3.97** | 6.82 | 5.63 | stopping fix alone |
| LiH | COBYLA | 692.65 | 587.74 | 663.55 | **298.54** | both needed |
| LiH | L-BFGS-B (finite diff) | 706.98 | 707.59 | 706.32 | 705.99 | nothing helps |
| LiH | L-BFGS-B (param-shift) | 408.97 | 398.93 | 14.88 | **3.84** | both needed |

**The free fix does not substitute for allocation quality.** On the cell that motivated
the whole question — LiH, L-BFGS-B with parameter-shift — refusing to stop moves uniform
from 408.97 to 398.93, recovering about **3%** of what Neyman bought. The hypothesis that
the Neyman benefit was "just" a termination artefact is false.

**Neither does allocation quality substitute for the free fix.** On H2O with COBYLA,
Neyman alone gets 982.82 to 952.70, which is nothing. The two together get it to 17.55 —
a 56x improvement that neither factor produces alone.

The reading that fits all six cells: **refusing to stop lets an optimiser spend its
budget; whether spending it helps depends on the signal being clean enough to make
progress with.** They are complementary, not alternatives.

## Two further results

**L-BFGS-B with finite-difference gradients cannot be rescued.** Roughly 1052 mHa on H2O
and 706 mHa on LiH regardless of allocation scheme, regardless of stopping rule, with the
full budget spent. A finite-difference gradient of a sampled energy is mostly noise, and
no amount of extra iterations on a noise gradient helps. The same optimiser with an
analytic parameter-shift gradient reaches 3.84 mHa on the same molecule and budget.

**The pilot is not always worth its 10%.** Best achievable with and without variance
estimation:

| molecule | optimiser | best without pilot | best with pilot | |
|---|---|---|---|---|
| H2O | COBYLA | 24.93 | **17.55** | pilot worth 7.4 mHa |
| H2O | L-BFGS-B (FD) | 1052.21 | 1052.22 | tie, both broken |
| H2O | L-BFGS-B (PS) | **3.97** | 5.63 | pilot not worth it |
| LiH | COBYLA | 438.59 | **298.54** | pilot worth 140.1 mHa |
| LiH | L-BFGS-B (FD) | 706.92 | 705.99 | tie, both broken |
| LiH | L-BFGS-B (PS) | 155.90 | **3.84** | pilot worth 152.1 mHa |

Worth it in 3 of 6, irrelevant in 2 (nothing works), actively counterproductive in 1.

## What this suggests in practice

In order, cheapest first:

1. **Use analytic gradients, not finite differences**, when the energy is sampled. This is
   the largest single effect here and it costs nothing extra.
2. **Do not let a noisy energy trip a convergence test.** Zero the tolerances and restart
   on stall. Also free.
3. **Then** variance-aware allocation buys a further large factor — 34x on H2O/COBYLA,
   104x on LiH/L-BFGS-B-PS, relative to step 2 alone.

Steps 1 and 2 are free; step 3 costs a 10% pilot and does not always pay for itself.

## Caveats

- Two molecules, one budget point (1e8 shots, 1e5 per evaluation). The parent study shows
  that at a 10x smaller evaluation budget none of this matters, because there the binding
  constraint is evaluation count and even exact arithmetic fails.
- "Restart from the final point" is one operationalisation of refusing to stop. It resets
  the L-BFGS-B Hessian approximation each time, which is not free — a variant that keeps
  the curvature history might do better.
- Statevector throughout, no gate or readout noise.
- Medians over 10 seeds. Several cells have wide per-seed spread; the raw records are here.

## Reproducing

```bash
SPSA_A=5.0 SPSA_C=0.1 python tools/shot_allocation_optimize.py LiH LBFGSB_ps_r neyman 100000000 100000 0 out/
python tools/analyse_early_stopping.py out/
```

Any of `COBYLA`, `LBFGSB`, `LBFGSB_ps` takes an `_r` suffix for the refuse-to-stop form.
