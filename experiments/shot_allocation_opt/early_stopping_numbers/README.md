# Early stopping, as numbers

1320 runs. The behavioural claim in the parent directory — that optimisers with a
convergence test mistake sampling noise for convergence and quit — measured directly
rather than inferred from outcomes.

2 molecules x 6 optimisers x 2 schemes x 5 noise levels x 10 seeds, plus exact-arithmetic
references. The evaluation cap is held at 1000 throughout and the **noise is swept**
(1e3 to 1e7 shots per evaluation), so termination is measured against signal quality with
the step allowance fixed. Each run records the evaluation at which the optimiser returned,
how many times it returned, and scipy's termination status and message.

## The claim needs splitting in three

It is true for one optimiser, weakly true for a second, and **false for the third**.

### Where each optimiser stops, first termination, of a 1000 cap

Median over 10 seeds, uniform allocation.

| molecule | optimiser | 1e3/eval | 1e4 | 1e5 | 1e6 | 1e7 | exact |
|---|---|---|---|---|---|---|---|
| H2O | COBYLA | 92 | 94 | 97 | 156 | 190 | **411** |
| H2O | L-BFGS-B (FD) | 318 | 325 | 325 | 318 | 292 | **403** |
| H2O | L-BFGS-B (PS) | 237 | 300 | 625 | 800 | 825 | **800** |
| LiH | COBYLA | 116 | 106 | 120 | 139 | 255 | **1000** |
| LiH | L-BFGS-B (FD) | 400 | 432 | 400 | 408 | 392 | **744** |
| LiH | L-BFGS-B (PS) | 325 | 310 | 310 | 852 | 1000 | **1000** |

**L-BFGS-B with parameter-shift gradients behaves exactly as the story predicts.** Its
stopping point tracks signal quality monotonically across four decades — LiH goes 325,
310, 310, 852, 1000 — and reaches the exact-arithmetic value once the signal is clean
enough. This is genuine noise-induced early stopping.

**COBYLA responds to noise, but only weakly, and never recovers.** H2O goes 92 to 190 as
noise falls by four decades, against 411 with exact arithmetic. Even at the cleanest
setting tested it stops at under half the exact value. Something other than sampling noise
is ending these runs as well.

**L-BFGS-B with finite differences does not respond to noise at all.** H2O: 318, 325, 325,
318, 292 — flat across four decades, against 403 exact. The early stop is real but it is
**not noise-graded**, so calling it noise-induced was wrong.

The mechanism is straightforward once stated. scipy's 2-point finite difference uses a
step of about `sqrt(eps)` ~ 1.5e-8, so the energy difference it is trying to resolve is of
order 1e-8 Ha. Sampling noise even at 1e7 shots per evaluation is of order 1e-4 Ha. The
signal-to-noise ratio is ~1e-4 at *every* noise level tested, which is why the curve is
flat: the gradient is equally destroyed everywhere. This is the same finding as the
early-stopping control, where finite differences could not be rescued by any allocation
scheme or stopping rule, now with the mechanism attached.

### Why it stops

Share of all terminations, pooled over default and refuse-to-stop forms (the "hit the cap"
entries are mostly the final return of a refuse-to-stop run).

| molecule / optimiser | reason | 1e3 | 1e4 | 1e5 | 1e6 | 1e7 |
|---|---|---|---|---|---|---|
| H2O / L-BFGS-B (PS) | no further decrease | 100% | 100% | 100% | 100% | 100% |
| LiH / L-BFGS-B (PS) | no further decrease | 100% | 100% | 100% | 100% | 100% |
| H2O / L-BFGS-B (FD) | no further decrease | 89% | 83% | 95% | 79% | 65% |
| | line search failed | 11% | 17% | 5% | 21% | 35% |
| LiH / L-BFGS-B (FD) | no further decrease | 93% | 81% | 84% | 80% | 79% |
| | line search failed | 7% | 19% | 16% | 20% | 21% |
| H2O / COBYLA | converged | 80% | 80% | 80% | 81% | 79% |
| | hit the cap | 20% | 20% | 20% | 19% | 21% |

The dominant mechanism is **"no further decrease"** — `REL_REDUCTION_OF_F <= FACTR*EPSMCH`.
The optimiser sees the noisy objective fail to improve and concludes it has converged. Line
search failure is a minority mode and, counter-intuitively, gets *more* common as the
signal gets cleaner.

A detail worth recording, because it defeats the obvious fix: **setting `ftol=0` does not
disable this test.** scipy converts `ftol` to `factr = ftol/eps`, so `ftol=0` tightens the
condition to "no reduction at all", which noisy evaluations still trigger. Runs with
`ftol=0.0, gtol=0.0` still terminate with `REL_REDUCTION_OF_F <= FACTR*EPSMCH`. The restart
loop, not the tolerance setting, is what keeps those runs going.

### How often it declares itself finished

Terminations per run in the refuse-to-stop forms; each one is a false convergence that was
overridden by a restart. Uniform allocation.

| molecule | optimiser | 1e3 | 1e4 | 1e5 | 1e6 | 1e7 |
|---|---|---|---|---|---|---|
| H2O | COBYLA_r | 4 | 4 | 4 | 4 | 4 |
| LiH | COBYLA_r | 3 | 3 | 3 | 3 | 3 |
| H2O | LBFGSB_r | 3 | 2 | 2 | 3 | 3 |
| LiH | LBFGSB_r | 2 | 2 | 2 | 2 | 2 |
| H2O | LBFGSB_ps_r | 3 | 3 | 2 | 1 | 1 |
| LiH | LBFGSB_ps_r | 2 | 3 | 3 | 1 | **0** |

Same split again. Parameter-shift L-BFGS-B declares convergence 2 to 3 times per run at
high noise and **zero** times at 1e7 shots per evaluation — it simply runs to the cap.
COBYLA declares 3 to 4 times regardless of signal quality.

### Does a cleaner signal delay the first stop?

First-stop evaluation, uniform -> neyman, at equal cost.

| molecule | optimiser | 1e3 | 1e4 | 1e5 | 1e6 | 1e7 |
|---|---|---|---|---|---|---|
| LiH | L-BFGS-B (PS) | 326 -> 326 | 310 -> 310 | **310 -> 589** | **434 -> 884** | 899 -> 852 |
| LiH | COBYLA | 116 -> 108 | 106 -> 111 | 120 -> 126 | **140 -> 226** | **255 -> 316** |
| LiH | L-BFGS-B (FD) | 400 -> 416 | 432 -> 392 | 400 -> 416 | 408 -> 368 | 392 -> 408 |

This closes the causal chain. At 1e5 shots per evaluation Neyman allocation delays LiH
L-BFGS-B-PS from 310 evaluations to 589 — a factor of 1.9 — and that is the same cell where
the parent study measured a 27x improvement in final energy and the scaling study measured
0/10 versus 7/10 seeds certifying. Better allocation buys outcome by buying iterations.

Finite differences show no effect at any noise level, consistent with everything above.

## Summary

- The dominant false-convergence mechanism is **"the noisy objective stopped decreasing"**,
  not line-search failure — 100% of parameter-shift terminations, ~80-95% of
  finite-difference ones.
- That mechanism is **strongly noise-graded for parameter-shift gradients**, weakly so for
  COBYLA, and **not at all for finite differences**, whose gradient is destroyed equally at
  every noise level because the differencing step is ~1e-8.
- A cleaner estimator delays the first stop by up to 1.9x, which is the mechanism by which
  allocation quality converts into final accuracy.
- `ftol=0` does not turn the test off. Only restarting does.

## Caveats

- Two molecules, 10 seeds, one evaluation cap (1000). Termination points have wide
  10th-90th ranges — H2O L-BFGS-B-PS at 1e5 spans 247 to 905 — so single-cell differences
  under about 1.5x are not meaningful here.
- The reason table pools default and refuse-to-stop runs to get enough terminations per
  cell; the "hit the cap" share is therefore an artefact of the refuse-to-stop design
  rather than a property of the optimiser.
- scipy's message strings are collapsed to labels by a regex in
  `tools/analyse_termination.py`; the raw messages are in every record.
- Statevector throughout, no gate or readout noise.

## Reproducing

```bash
python tools/shot_allocation_optimize.py LiH LBFGSB_ps uniform 100000000 100000 0 out/
python tools/analyse_termination.py out/
```

Every record carries a `termination` list with the evaluation count, scipy status code and
message for each optimiser return.
