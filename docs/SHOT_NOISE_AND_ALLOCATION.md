# Shot noise, allocation, and optimiser failure in VQE

**A technical note.** 4,888 runs, 10 molecules, 20 to 919 Pauli terms.
Data: `experiments/shot_allocation/`, `experiments/shot_allocation_opt/`.
Hashes and provenance: `experiments/MANIFEST.json`.

---

## Summary

A VQE energy is a weighted sum over Pauli terms, `E = Σᵢ cᵢ⟨Pᵢ⟩`, and every term must be
sampled. Shots are the dominant cost of running VQE, so how they are spent is a first-order
question. This note reports what we measured about that, and — more usefully — about which
of several plausible explanations for VQE optimiser failure actually hold.

**The ranked recommendations, cheapest first.** The order matters: the first two cost
nothing and are worth more than the third, which is the one most people reach for.

> **1. Use analytic gradients, never finite differences, on a sampled energy.**
> A finite-difference gradient of a sampled energy is noise at every shot budget we
> tested. It cannot be rescued by better allocation, by more iterations, or by disabling
> early stopping. This is the single largest effect in the study and it costs nothing.
>
> **2. Do not let a noisy energy trip a convergence test.**
> Optimisers stop because the sampled objective stopped decreasing, conclude they have
> converged, and quit with most of the budget unspent. Also free. Note that setting
> `ftol=0` does **not** achieve this — see §3.
>
> **3. Only then, variance-aware (Neyman-style) shot allocation, with safeguards.**
> Worth a further 34× to 104× on top of 1 and 2 in the cells where it works. But it costs
> a ~10% pilot pass, it does not always pay for itself, and implemented naively it is
> catastrophically biased — see §4.

**And a boundary condition that governs all three:** below roughly 10⁸ total shots for
these systems, *none of it matters*, because the binding constraint is the number of
optimiser evaluations rather than the noise on each one. §5.

---

## 1. Method, and one thing worth copying

Every claim below is measured against an **exact-arithmetic control**: the identical
optimiser, identical seed, identical evaluation cap, with sampling switched off entirely.

This is the most transferable part of the note. A noisy run that matches its exact control
was never limited by measurement, and no amount of shot-allocation cleverness can help it.
Without that control it is very easy — we did it — to attribute a failure to noise when
noise was contributing almost nothing. Running the zero-noise control *first* also caught
two bugs in our own harness that would otherwise have invalidated an entire grid.

Other conventions:

- **Shots are counted per term**, so a run's total cost is exactly `Σᵢ sᵢ`. Grouping
  commuting terms into joint measurements is an orthogonal saving that composes with
  everything here and is deliberately not modelled. No claim depends on it.
- **Every scheme is charged the same budget.** Variance-aware allocation pays for its
  pilot out of that budget, not on top of it.
- **Scoring is on RMSE, never standard deviation.** §4 explains why that distinction
  turned out to be decisive.
- Sampling draws each term from `Binomial(s, (1+⟨P⟩)/2)`. For a ±1 observable this is the
  exact sampling distribution rather than an approximation, which is what makes 200 repeats
  across 919 terms affordable. Tested against real circuit execution in
  `experiments/shot_allocation/binomial_check.py`: ratios 1.026 and 0.950 against a ±0.196
  noise band.
- Single-threaded BLAS pinned before NumPy import, as everywhere in this repository.
  Parallelism is across processes only, so no run can perturb another's arithmetic.

---

## 2. Recommendation 1 — analytic gradients

Two forms of the same optimiser, L-BFGS-B, differing only in how the gradient is obtained.
Median first-termination evaluation of a 1000 cap, uniform allocation, against noise:

| gradient | 10³/eval | 10⁴ | 10⁵ | 10⁶ | 10⁷ | *exact* |
|---|---|---|---|---|---|---|
| finite difference (H₂O) | 318 | 325 | 325 | 318 | 292 | *403* |
| finite difference (LiH) | 400 | 432 | 400 | 408 | 392 | *744* |
| parameter-shift (H₂O) | 237 | 300 | 625 | 800 | 825 | *800* |
| parameter-shift (LiH) | 325 | 310 | 310 | 852 | 1000 | *1000* |

Parameter-shift tracks signal quality monotonically and reaches the exact-arithmetic value
once the signal is clean. Finite differences are **flat across four decades of noise**.

*A run that never declared convergence is counted at its full evaluation count, because it
never stopped.* That is not a bookkeeping detail — the fraction of such runs is the
cleanest single statement of the effect. Number of seeds out of 10 that never declared
convergence, uniform allocation:

| optimiser | 10³ | 10⁴ | 10⁵ | 10⁶ | 10⁷ |
|---|---|---|---|---|---|
| L-BFGS-B parameter-shift (LiH) | 0/10 | 0/10 | 0/10 | **4/10** | **7/10** |
| L-BFGS-B parameter-shift (H₂O) | 0/10 | 0/10 | 0/10 | 0/10 | 1/10 |
| L-BFGS-B finite difference (both) | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |
| COBYLA (both) | 0/10 | 0/10 | 0/10 | 0/10 | 0/10 |

Give parameter-shift a clean enough signal and it simply stops declaring false convergence.
Finite differences and COBYLA declare convergence in every single run at every noise level
tested.

The mechanism: scipy's 2-point differencing uses a step of about `√eps ≈ 1.5e-8`, so the
energy difference it must resolve is of order 10⁻⁸ Ha, while sampling noise even at 10⁷
shots per evaluation is of order 10⁻⁴ Ha. The signal-to-noise ratio is ~10⁻⁴ at *every*
level tested, which is why the curve is flat — the gradient is equally destroyed
everywhere. It is not noise-graded, so it cannot be fixed by reducing noise.

Consistent with that, in the 2×2 of §3 finite differences sit at ~1052 mHa (H₂O) and ~706
mHa (LiH) regardless of allocation scheme *or* stopping rule, with the full budget spent.
The same optimiser with a parameter-shift gradient reaches 3.84 mHa on the same molecule
and budget.

---

## 3. Recommendation 2 — prevent noisy early stopping

**Why they stop.** Share of all terminations, by scipy's reported reason:

| optimiser | reason | 10³ | 10⁴ | 10⁵ | 10⁶ | 10⁷ |
|---|---|---|---|---|---|---|
| L-BFGS-B, parameter-shift | no further decrease | 100% | 100% | 100% | 100% | 100% |
| L-BFGS-B, finite diff | no further decrease | 89% | 83% | 95% | 79% | 65% |
| | line search failed | 11% | 17% | 5% | 21% | 35% |
| COBYLA | reports convergence | 80% | 80% | 80% | 81% | 79% |

The dominant mode is **`REL_REDUCTION_OF_F <= FACTR*EPSMCH`** — the optimiser sees the
noisy objective fail to improve and concludes it is done. Line-search failure is a minority
mode and, counter-intuitively, becomes more common as the signal gets *cleaner*.

> **A trap worth recording.** Setting `ftol=0` does **not** disable this test. scipy maps
> `ftol` to `factr = ftol/eps`, so `ftol=0` merely tightens the condition to "no reduction
> at all", which noisy evaluations still trigger. Runs configured with `ftol=0.0, gtol=0.0`
> still terminate with `REL_REDUCTION_OF_F <= FACTR*EPSMCH`. What works is **restarting
> the optimiser from its own final point** until the budget is spent. In our runs that
> takes 2 to 4 restarts.

**How much it is worth, and what it is not.** The 2×2 of allocation quality against
permission to keep going. Median gap over 10 seeds, 10⁸ shots at 10⁵ per evaluation:

| molecule | optimiser | uniform, default stop | uniform, no stop | neyman, default stop | neyman, no stop | |
|---|---|---|---|---|---|---|
| H₂O | COBYLA | 982.82 | 586.55 | 952.70 | **17.55** | both needed |
| H₂O | L-BFGS-B (FD) | 1060.49 | 1052.21 | 1062.70 | 1052.22 | nothing helps |
| H₂O | L-BFGS-B (PS) | 15.79 | **3.97** | 6.82 | 5.63 | stopping alone |
| LiH | COBYLA | 692.65 | 587.74 | 663.55 | **298.54** | both needed |
| LiH | L-BFGS-B (FD) | 706.98 | 707.59 | 706.32 | 705.99 | nothing helps |
| LiH | L-BFGS-B (PS) | 408.97 | 398.93 | 14.88 | **3.84** | both needed |

**Neither fix substitutes for the other.** Refusing to stop recovers only ~3% of what
allocation buys on LiH/parameter-shift. Allocation alone recovers essentially nothing on
H₂O/COBYLA. Together they take that cell from 982.82 to 17.55 mHa — 56×, which neither
factor produces alone.

The reading that fits all six cells: *refusing to stop lets an optimiser spend its budget;
whether spending it helps depends on the signal being clean enough to make progress with.*

**The chain, end to end.** Better allocation buys outcome by buying iterations. LiH with
parameter-shift gradients, first-stop evaluation, uniform → neyman at equal cost:

| shots/eval | 10³ | 10⁴ | 10⁵ | 10⁶ | 10⁷ |
|---|---|---|---|---|---|
| first stop | 326 → 326 | 310 → 310 | **310 → 822** | 852 → 1000 | 1000 → 1000 |

At 10⁵ shots per evaluation a cleaner estimator delays the first stop by 2.7×, and that is
the same cell where the outcome studies measure 27× in final energy and 0/10 versus 7/10
seeds certifying. Finite differences show no delay at any noise level.

---

## 4. Recommendation 3 — variance-aware allocation, and how to get it wrong

Neyman allocation gives term *i* a share proportional to `|cᵢ|·σᵢ`, which minimises the
variance of a weighted sum of independent estimators. In VQE it should beat uniform
because term variances are wildly unequal — a Pauli string near an eigenoperator of the
current state has σ ≈ 0, so shots spent on it buy nothing.

**Implemented naively it is catastrophic.** σ must be estimated from a pilot sample, and
`σ̂ = √(1 − m²)` is **exactly zero** whenever the pilot draw comes out all-heads or
all-tails — likely for a near-deterministic term. A term with `σ̂ = 0` receives zero shots
and is then dropped from the energy sum entirely. And near-deterministic Pauli strings
carry the *largest* coefficients, so the rule preferentially deletes the terms that matter
most:

- deleted terms carried **9.1× the mean |cᵢ|** of terms kept
- a median of **48% of λ = Σ|cᵢ|** silently removed
- median RMSE **603.70 mHa**, against **11.35 mHa** for plain uniform allocation

It has the **smallest standard deviation of any scheme in the study** (5.75 mHa against
uniform's 11.36). Its estimates are tightly clustered — hundreds of millihartree from the
right answer. This is why nothing here is scored on spread.

**The safeguards.** Two repairs, both cheap:

1. **Shrink the variance estimate.** Use the Agresti-Coull proportion `p = (k+1)/(n+2)`,
   which is never exactly 0 or 1, so `σ̂` is never exactly zero and no term is starved. Add
   a floor of one shot per term.
2. **Pool the pilot with the main pass.** The pilot already measured every term and you
   have already paid for it; discarding it is waste.

```python
p_ac  = (k + 1.0) / (n_pilot + 2.0)          # never 0 or 1
sigma = 2.0 * np.sqrt(p_ac * (1.0 - p_ac))
alloc = np.floor(np.abs(c) * sigma / np.sum(np.abs(c) * sigma) * budget) + 1
mean  = (n_pilot * m_pilot + s * m_main) / (n_pilot + s)
```

Scored on RMSE over 270 estimator runs:

| scheme | median RMSE | vs uniform | beats uniform |
|---|---|---|---|
| uniform | 11.35 mHa | 1.00× | — |
| weighted by \|cᵢ\| | 9.68 mHa | 1.17× | 58/90 |
| naive Neyman | 603.70 mHa | 0.04× | 22/90 |
| shrinkage only | 8.88 mHa | 1.45× | 81/90 |
| **shrinkage + pooling** | **8.49 mHa** | **1.53×** | **84/90** |
| oracle (exact σ) | 7.41 mHa | 1.69× | 86/90 |

1.53× in RMSE is **2.33× fewer shots** for equal accuracy, holding across all 10 molecules
(1.25×–1.99×), all three parameter states and all three budgets. The pilot costs 6% over
the exact-σ ceiling.

**It does not always pay.** Across the six optimiser cells of §3, the pilot is worth it in
three (+7.4, +140.1, +152.1 mHa), irrelevant in two where nothing works, and *actively
counterproductive* in one — H₂O with parameter-shift, where uniform plus the free stopping
fix reaches 3.97 mHa and adding the pilot gives 5.63.

---

## 5. The boundary condition: when none of this matters

Success rate — seeds reaching under 10 mHa out of 10, refuse-to-stop forms, 10⁵ shots per
evaluation:

| molecule / optimiser | scheme | 10⁶ | 3×10⁶ | 10⁷ | 3×10⁷ | 10⁸ |
|---|---|---|---|---|---|---|
| H₂O / COBYLA | uniform | 0 | 0 | 0 | 0 | 0 |
| | neyman | 0 | 0 | 0 | 0 | 2 |
| | *exact* | 0 | 0 | *5* | *10* | *10* |
| LiH / L-BFGS-B (PS) | uniform | 0 | 0 | 0 | 0 | 0 |
| | weighted | 0 | 0 | 0 | 0 | 3 |
| | neyman | 0 | 0 | 0 | 0 | **7** |
| | *exact* | 0 | 0 | 0 | 0 | *10* |

**Below 10⁸ shots, nothing works under sampling noise** — every scheme, every optimiser,
0/10 from 10⁶ through 3×10⁷. Allocation quality is irrelevant across that whole range, not
because it fails but because nothing succeeds. What binds there is evaluation count, and
the exact-arithmetic control proves it: at 100 evaluations LiH with L-BFGS-B fails at
**651.67 mHa with perfect arithmetic**, against 707.85 with uniform sampling. Sampling
noise accounts for 56 of the 707 mHa; the other 92% is simply too few evaluations.

**The measurement penalty is worth more than 30× in budget.** H₂O with COBYLA certifies
10/10 on exact arithmetic at 3×10⁷ shots; the best noisy scheme manages 2/10 at 10⁸.

**The onset is abrupt.** LiH/parameter-shift runs at 1.01×, 1.01×, 1.01×, 1.06× across
four budget decades and then 104× in the last step. Nothing in the first four points
predicts the fifth, so this crossover cannot be interpolated — a warning against
extrapolating from two budget points, which is how we got it wrong the first time.

**Report success rates, not medians.** The per-seed outcome is bimodal: a run either
catches and converges or stays stuck. LiH, parameter-shift, 10⁸ shots, Neyman, ten seeds:

```
1.5   2.3   2.8   3.5   3.5   4.2   4.8   26.3   176.7   255.9    mHa
```

Seven converged, two did not. The 3.84 median is a true statement about that set and a
misleading summary of it.

---

## 6. A note on SPSA

SPSA is the standard recommendation for noisy VQE and had not been tested in this suite.
It **required calibration before any noisy result could be believed**: with textbook
default gains it never moved at all, sitting at 722 mHa after 5000 *exact-arithmetic*
evaluations. A sweep at zero noise over `a ∈ {0.5…20}`, `c ∈ {0.05, 0.1, 0.2}`
(`experiments/shot_allocation_opt/spsa_calibration/`) selected `a = 5.0, c = 0.1`, which
reaches 1.97 mHa.

Its real advantage is not noise robustness in the usual sense. It has **no convergence
test to trip**, so it always spends its budget, and it costs 2 evaluations per iteration
regardless of parameter count where parameter-shift costs 2N.

The general point: an optimiser comparison in which one method is untuned measures tuning,
not the method.

---

## 7. What this does not establish

- **Statevector simulation throughout.** No gate noise, no readout error, no device
  topology. Sampling noise is zero-mean; gate noise is not, and nothing here transfers to
  it.
- **Two molecules in the optimisation studies** (LiH, H₂O), ten in the estimator study.
  Nothing here establishes behaviour at 20 qubits.
- **Shots counted per term.** Commuting-group measurement is a separate and larger saving,
  not modelled.
- **Ten seeds per cell.** With a bimodal outcome that resolves a success rate to about one
  decimal place; 2/10 versus 3/10 is not a distinction this data supports.
- **The optimisation studies are a reconstruction at matched scale**, not a bit-identical
  replay of the archived failure — those used grouped-Hamiltonian measurement and stopped
  at 14 evaluations. The qualitative failure reproduces; the trajectory does not.
- **One shots-per-evaluation setting in the scaling curves** (10⁵), and the curve stops at
  10⁸ with several cells still climbing. The crossover is bracketed as "at or above 10⁸",
  not located.

---

## 8. Corrections to earlier claims

Recorded because the corrections are part of the result.

| Claim | Status |
|---|---|
| Gradient-optimiser shot budget scales with Hamiltonian size | **Falsified.** Extending from 2 to 8 molecules killed it |
| "1000 shots per energy evaluation" in an earlier post | **Wrong by 12–101×.** PennyLane charges per commuting group. That post was withdrawn, not patched |
| Neyman allocation gives 8.9× on LiH | **Wrong.** Measured at a random start, on standard deviation only, on two molecules. The validated figure is ~1.5× RMSE, ~2.3× shots |
| The LiH collapse was largely a measurement problem | **Wrong.** 92% of it was evaluation starvation; the exact-arithmetic control still fails at 652 mHa |
| Optimisers mistake sampling noise for convergence | **True for parameter-shift, weak for COBYLA, false for finite differences**, whose early stop is not noise-graded at all |

---

## 9. Reproducing

```bash
# estimator study
python tools/shot_allocation.py <molecule> <state> <budget> <outdir>
python tools/analyse_shot_allocation.py <outdir>

# optimisation studies — append _r to an optimiser name for the refuse-to-stop form
SPSA_A=5.0 SPSA_C=0.1 \
  python tools/shot_allocation_optimize.py <mol> <opt> <scheme> <total> <per_eval> <seed> <outdir>
python tools/analyse_shot_allocation_optimize.py <outdir>
python tools/analyse_early_stopping.py <outdir>
python tools/analyse_termination.py <outdir>
```

`state` is `start`, `mid` or `converged`; `scheme` is `uniform`, `weighted`, `neyman` or
`exact`. Optimisers: `COBYLA`, `LBFGSB`, `LBFGSB_ps`, `Adam`, `SPSA`.

Every record now carries a `provenance` block in the same shape as a certified suite
entry — `tool_versions` including the git commit, and an `environment` block asserting
BLAS threads are pinned. The 4,888 runs committed before that block existed are covered by
`experiments/MANIFEST.json`, which records the environment they were produced in together
with a per-file `SHA256SUMS` in each study directory:

```bash
cd experiments/shot_allocation_opt/budget_scaling && sha256sum -c SHA256SUMS
```

Failed, superseded and falsified runs are retained throughout.

**Every figure in this note is checked against the committed data**, not transcribed from
a working session:

```bash
python tools/verify_shot_noise_note.py
```

recomputes each quoted number from the JSON records and prints PASS or FAIL per claim,
exiting non-zero if any disagrees. It is worth re-running after any change to the data or
the analysis scripts; it caught a definitional error in a draft of this note, where a
first-stop figure had been taken over only the runs that stopped rather than over all runs.
