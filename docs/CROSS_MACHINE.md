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

**Measured since: a container image does close it.** Built once and moved to both
machines, with the kernel forced and the C library fixed, the same six entries that differ
by up to 6 mHa on bare metal are bit-identical across the two processors -- zero of six
reproduce without it, six of six with it. The prediction in this paragraph held, and the
cost is that the published suite would have to be regenerated inside the image to
reproduce there. See [REFERENCE_ENVIRONMENT.md](REFERENCE_ENVIRONMENT.md).

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

## Two more measurements, 2026-09-09

**The kernel can change the number of qubits, not only the last bit.** Cyclobutadiene's
CASSCF active orbitals are fixed only by the optimiser's path, so the two kernels converge
to different orbital gauges of the same energy — and the two gauges do not have the same
Z₂ symmetry structure. Under Haswell the pipeline finds three symmetries and tapers C₄H₄
to five qubits; under SkylakeX it finds two and tapers to six, which is what the two
published C₄H₄ Jordan–Wigner entries store. The CASCI energies agree to 2 × 10⁻¹⁰ Ha, so
this is a symmetry-detection tolerance landing on opposite sides of a threshold, not
different physics. The consequence is sharp: on the workstation those two entries' UCCSD
and ADAPT operator pools cannot be rebuilt at all, and the noisy tier recorded them as
failed. Re-run on the cluster, whose kernel is the one they were generated under, the
re-derived Hamiltonian matches the stored coefficients exactly (maximum deviation 0.0), the
rebuild gate passes at 3 × 10⁻¹³ Ha, and both are measured. That is how the published
records were produced, and every noisy-tier record now carries the machine fingerprint that
says so ([`NOISY_TIER.md`](NOISY_TIER.md)).

**An entry that converges exactly reproduces across machines to the last bit.** The
packaging suite regenerates H₂ and pins its hash. H₂ tapers to one qubit and its
optimisation converges rather than stopping on a tolerance, and the entry regenerated on
the AVX2 workstation hashes to the same value as the one recorded on the reference
machine: `375960cd...`, every number in the file identical. Machine-boundness is a property
of runs that stop on a comparison, not of the arithmetic in general.

**The machine fingerprint is recorded but not hashed.** Adding it on 2026-09-07 put it
inside the hashed part of provenance, which meant a regeneration on a different machine
produced a different entry hash even when every number was identical — destroying exactly
the comparison the hash exists to support. It is now in `_HASH_EXCLUDE`, in the pipeline
and in `scripts/verify_entry.py` alike, alongside the timestamps and the git commit. No
published entry is affected: all 54 predate the field, and their hashes recompute
unchanged.

---

## What it does and does not change

**Certification survives the change of machine for 44 of the 47 certified entries.**
Every one of them has now been measured on both machines: the last seven, the largest
Jordan–Wigner entries, were re-verified on 2026-09-09, the slowest of them taking four and
a half hours. The claim certification makes is that the gap is below 0.01 Ha, which is 10⁴
times larger than most of the movement measured here. Three entries do not survive:

| entry | published gap | on the other machine | moved | |
|---|---|---|---|---|
| C₄H₄ parity HEA | 3.83 mHa | 11.83 mHa | 7.99 mHa | does not certify |
| N₂ parity HEA, 10 layers | 4.40 mHa | 10.94 mHa | 6.54 mHa | does not certify |
| N₂ Jordan–Wigner HEA, 10 layers | 4.51 mHa | 20.37 mHa | 15.85 mHa | does not certify |

All three are hardware-efficient, and each moved further than its own margin. They are
flagged **fragile** on the leaderboard rather than withdrawn, because each reproduces
exactly on the machine that generated it, which is what its provenance describes.

The third was found in the last batch and is the largest movement measured anywhere in
this work: 15.85 mHa, three times its own margin, on an entry whose optimiser is
**L-BFGS-B**. That is the second L-BFGS-B entry to lose certification across machines, and
both are N₂ at ten layers with `multistart_requested: 5`, `multistart: 1` and
`early_stopped: true` — the loop stopped at the first attempt that cleared the bar. The
gradient-free/gradient-based distinction does not explain either of them; the stopping test
does. See "The optimiser rule, corrected" below, which now rests on two independent
instances rather than one.

Two more certify on both machines but moved further than their own margin, so they passed
only because the movement happened to shrink the gap. They are flagged **marginal**: a
pass whose sign was favourable is not evidence of stability.

| entry | published gap | on the other machine | moved |
|---|---|---|---|
| C₄H₄ Jordan–Wigner HEA | 9.64 mHa | 8.18 mHa | 1.45 mHa, 4.0× its margin |
| C₄H₄ Jordan–Wigner UCCSD | 7.92 mHa | 1.91 mHa | 6.01 mHa, 2.9× its margin |

**Nothing about the physics changes**, no entry's energy is edited, and no hash is
touched. What changes is what the leaderboard claims: robustness is now a measurement on
all 47 certified entries rather than a prediction on 5. The final counts are 42 robust,
2 marginal, 3 fragile.

The seven entries measured last are worth reading as a group, because they are the ones
the earlier text had to call unmeasured:

| entry | moved | margin | |
|---|---|---|---|
| H₈ Jordan–Wigner ADAPT | 0.00000001 mHa | 0.20 mHa | robust |
| H₆ Jordan–Wigner ADAPT | 0.0001 mHa | 0.73 mHa | robust |
| H₁₀ Jordan–Wigner ADAPT | 0.001 mHa | 0.02 mHa | robust |
| benzene Jordan–Wigner HEA | 0.11 mHa | 1.26 mHa | robust |
| benzene Jordan–Wigner ADAPT | 0.35 mHa | 0.46 mHa | robust |
| N₂ Jordan–Wigner ADAPT | 0.94 mHa | 1.17 mHa | robust |
| N₂ Jordan–Wigner HEA, 10 layers | 15.85 mHa | 5.49 mHa | fragile |

**H₁₀ has the smallest certification margin in the suite, 0.02 mHa, and it survived.** It
moved 0.001 mHa, a twentieth of its margin, on an 18-qubit ADAPT circuit with 300 selected
operators that takes four and a half hours to re-verify. Size and tightness of margin are
not what predicts fragility here. The three that failed are all hardware-efficient
ansätze; the six largest ADAPT entries in the suite are among the steadiest things in it.

A label was also withdrawn on 2026-09-09, before that measurement existed. H₁₀ had been
shown as robust on the strength of an older study of a different perturbation — the same
entry re-run under drifted package versions — because the export consulted that study
whenever the cross-machine table had no verdict. "No verdict" meant the entry had never
been re-run on a second machine, which is a thing to say rather than to fill in. The table
now takes precedence whenever it knows an entry at all. H₁₀ has since earned the label it
was being given for the wrong reason, which is the order those two things should happen
in.

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
4. **DONE 2026-09-09.** The seven entries that had only been verified on the machine
   that made them — H₆, H₈, H₁₀, N₂ and benzene under Jordan–Wigner — were re-verified on
   the second machine, 15,559 s for H₁₀ alone. Six are robust; N₂ Jordan–Wigner HEA is
   fragile. No entry in the suite is now classified without a measurement behind it.
