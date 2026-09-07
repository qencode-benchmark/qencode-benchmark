# Bit-for-bit reproduction is machine-bound

Every certified QEncode entry records the software that produced it: Python, PennyLane,
NumPy, PySCF, SciPy, OpenFermion, the git commit, and that BLAS ran on a single thread.
Since the threading work of July, that was believed to pin reproducibility completely.

It does not. On 2026-09-07 the whole suite was re-verified on a second machine running
exactly the same pinned stack. **Every entry reproduced bit-for-bit on the machine that
generated it, and moved on the other one** — by between 10⁻¹⁶ and 8 × 10⁻³ Ha. Two
certified entries lost certification in the move.

Tool: `scripts/verification_sweep.py`. Data: `experiments/cross_machine/measurements.json`,
built by `tools/build_cross_machine_table.py`. Records: `experiments/verification_sweep/`.

---

## The two machines

Identical package versions, identical pins, identical seeds, one BLAS thread on both.

| | workstation | cluster |
|---|---|---|
| CPU | AMD Ryzen Threadripper 2990WX | Intel Xeon Silver 4316 |
| vector instructions | FMA, AVX2 | FMA, AVX2, **AVX-512** |
| libc | glibc 2.39 | glibc 2.34 |
| OS | Ubuntu 24.04.3 (WSL2) | AlmaLinux 9.3 |
| stack | PennyLane 0.45.0, NumPy 2.2.6, PySCF 2.6.2, SciPy 1.13.1, OpenFermion 1.6.1, Python 3.11.15 | identical |

---

## What was measured

Two sweeps in opposite directions, both in `strict` mode, where the regenerated energy
must match the stored one to 10⁻⁶ Ha.

**On the cluster, all 54 entries.** 48 passed, 6 failed. The 36 entries generated on the
cluster reproduced with an energy difference of *exactly zero* — including H₁₀ ADAPT, the
largest in the suite at 18 tapered qubits and 300 operators, which took two hours. The 18
entries regenerated on the workstation the previous day all moved.

**On the workstation, 23 of the Jordan–Wigner entries** (the rest are too slow to verify
there). **None reproduced bit-for-bit.** All 23 moved, 13 by less than 10⁻⁶ Ha and 10 by
more, the largest 6.0 × 10⁻³ Ha. All 23 still certified.

The pattern is exact and has no exceptions: an entry reproduces bit-for-bit on its own
machine and nowhere else.

---

## Why

Below the packages the arithmetic differs. OpenBLAS dispatches kernels by CPU at run time,
so a machine with AVX-512 sums a dot product in a different order from one with only AVX2,
and floating-point addition is not associative. The two systems' `libm` differ as well.
Neither difference is a bug, and neither is visible in a version number.

The differences are last-bit, around 10⁻¹⁶ relative. They become macroscopic through the
same mechanism the threading result describes: any step that makes a *decision* by
comparing two nearly equal energies can flip, and a single flipped comparison early in an
optimisation sends the trajectory to a different local minimum. COBYLA compares sampled
energies at every step. A multistart loop compares against the certification threshold to
decide whether to stop.

This is the machine-level analogue of the threading finding, and it is the same lesson:
**an entry that does not record where it ran cannot say where it reproduces exactly.**

Since 2026-09-07 the pipeline records a machine fingerprint in
`provenance.environment.machine` — CPU model, vector instruction sets, libc, OS. The 54
entries published before that date do not carry it, and for them the generating machine is
inferred from which one reproduces them bit-for-bit.

---

## Where exactly it enters, and what fixes what

Measured by forcing both machines onto the same BLAS kernel (`OPENBLAS_CORETYPE=Haswell`,
the workstation's native kernel, with NumPy's AVX-512 dispatch disabled on the cluster) and
regenerating the same entries on both.

| stage | same kernel on both | result |
|---|---|---|
| PySCF: qubit Hamiltonian, HF energy, CASCI energy | yes | **bit-identical**, every coefficient, LiH and C₄H₄ (CASSCF) alike |
| PySCF, native kernels (Haswell vs SkylakeX) | no | coefficients differ by up to 3 × 10⁻⁵ Ha (N₂ CASSCF), 10⁻¹⁵ (LiH) |
| PennyLane: energy at a fixed parameter vector | either | **bit-identical** energy and statevector, across machines *and* across kernels |
| COBYLA trajectory, identical Hamiltonian and energy function | yes | still diverges: LiH parameters 3 × 10⁻⁹ apart (energy 8 × 10⁻¹² Ha); C₄H₄ parameters 0.22 apart (energy 1.6 × 10⁻⁴ Ha) |

Three things follow.

**The electronic-structure half of the pipeline is fully deterministic once the kernel is
pinned.** The "different orbital gauge" that [`NOISY_TIER.md`](NOISY_TIER.md) and
[`SECTOR_FIX.md`](SECTOR_FIX.md) attribute to CASSCF converging differently on another day
is the BLAS kernel and nothing else: force the kernel and the gauge is identical. The
reference-energy spread of 4.2 × 10⁻¹⁰ Ha in the packaged table has the same cause.

**The variational half is not, even then.** With the Hamiltonian identical and the energy
function returning identical bits for the same input, the two machines' COBYLA runs still
part ways. The energy function is not the culprit; something in the loop around it is. A
direct probe of the C libraries shows `sin`, `cos`, `exp`, `log`, `sqrt` and `atan2`
returning identical bits on both machines but `expm1` differing (glibc 2.34 against 2.39),
so the two libraries are not identical, and NumPy's reductions can also group terms
differently depending on where the allocator happens to place an array. Which of these
moves COBYLA has not been isolated. What is established is that it is below the level of
the energy evaluation.

**So there are two fixes of different strength.** Pinning the kernel is cheap, makes the
Hamiltonian portable across x86 machines, and shrinks the movement of well-conditioned
runs to ~10⁻¹¹ Ha, which passes strict verification (10⁻⁶) across machines. It does not
give bit-for-bit reproduction of a poorly conditioned gradient-free run. That needs
identical arithmetic all the way down — the same C library as well as the same kernel —
which in practice means a container image, and that is the right form for a reference
environment that claims bit-for-bit.

Neither fix is applied to the published suite here. Pinning the kernel would make the
cluster's own entries, generated under SkylakeX, stop reproducing exactly on the cluster
until regenerated, and a suite-wide regeneration is a decision, not a patch. The pipeline
now records which kernel was selected, so every entry from today says which kernel it
reproduces under.

---

## What it does and does not change

**Certification survives the change of machine for 38 of the 40 certified entries that
were measured on a second machine.** Seven certified entries — the largest Jordan–Wigner
ones — have not been, and are reported as unmeasured rather than counted as survivors. The
claim certification makes is that the gap is below 0.01 Ha, which is 10⁴ times larger
than most of the movement measured here. Two entries do not survive:

| entry | published gap | on the other machine | |
|---|---|---|---|
| C₄H₄ parity HEA | 3.83 mHa | 11.83 mHa | does not certify |
| N₂ parity HEA, 10 layers | 4.40 mHa | 10.94 mHa | does not certify |

Both are hardware-efficient parity entries, and both moved further than their own margin.
They are flagged **fragile** on the leaderboard rather than withdrawn, because each
reproduces exactly on the machine that generated it, which is what its provenance
describes.

Two more certify on both machines but moved further than their own margin, so they passed
only because the movement happened to shrink the gap. They are flagged **marginal**: a
pass whose sign was favourable is not evidence of stability.

| entry | published gap | on the other machine | moved |
|---|---|---|---|
| C₄H₄ Jordan–Wigner HEA | 9.64 mHa | 8.18 mHa | 1.45 mHa, 4.0× its margin |
| C₄H₄ Jordan–Wigner UCCSD | 7.92 mHa | 1.91 mHa | 6.01 mHa, 2.9× its margin |

**Nothing about the physics changes**, no entry's energy is edited, and no hash is
touched. What changes is what the leaderboard claims: robustness is now a measurement on
40 entries rather than a prediction on 5.

---

## The optimiser rule, corrected

The suite predicts fragility from the configuration: a gradient-free optimiser on an
unstructured ansatz amplifies, ADAPT and gradient-based runs do not. Measured against 54
entries on two machines, that rule is a useful *susceptibility* indicator and not a
predictor:

- Of the 38 entries the rule calls amplifying, **21 did not move at all** on the machine
  that generated them and moved only slightly on the other. Being susceptible is not being
  unstable.
- **One entry the rule calls safe moved the second-most of any entry.** N₂ parity
  hardware-efficient at ten layers uses L-BFGS-B with analytic gradients, and it moved
  6.5 mHa, enough to lose certification. Its Jordan–Wigner counterpart, same optimiser and
  same depth, reproduced at exactly zero.

The distinguishing feature is not the optimiser's use of gradients. It is whether the run
contains a **comparison that steers control flow**. That entry's multistart loop stops as
soon as an attempt certifies; it stopped after 2 restarts on one machine, and the decision
of whether restart 1 was good enough is a comparison against a threshold. The Jordan–Wigner
counterpart stopped after 1.

So the rule should read: a run amplifies if any decision it makes — the optimiser's next
step, or the loop's decision to stop — is taken by comparing quantities that can differ in
their last bits. Gradient-free optimisation is the commonest such decision, not the only
one.

---

## What should follow

1. **Record the machine.** Done, for entries generated from 2026-09-07.
2. **Say which machine a strict verification is meaningful on.** `verify_entry.py --mode
   strict` is a same-machine test. On a different machine the honest question is
   `--mode certification`, which asks whether the gap still clears the bar.
3. **Do not treat bit-for-bit reproduction as the definition of a reproducible benchmark.**
   It is achievable, it is worth recording, and it is a property of a machine rather than
   of a result. Certification is the portable claim.
4. **The 7 unmeasured entries** — H₆, H₈, H₁₀, N₂ and benzene under Jordan–Wigner — have
   only been verified on the machine that made them, because verifying them on the other
   takes hours each. They are reported as unmeasured, not as robust.
