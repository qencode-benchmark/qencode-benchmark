# The suite is unbalanced, and it costs accuracy

Status: **measured, staged, not merged.** Suite v4.4 is frozen until the paper it
underpins is published, so nothing here changes `releases/v4/db`, the leaderboard, or any
figure in the draft. The candidate entries are in `experiments/rebalance/candidates/`.

## What the distribution actually is

Counted over all 54 published entries:

| axis | distribution |
|---|---|
| ansatz | hardware-efficient 29 (54%), UCCSD 15 (28%), ADAPT-VQE 10 (18%) |
| optimiser as recorded | COBYLA 39, ADAPT/COBYLA 8, L-BFGS-B 5, ADAPT/L-BFGS-B 2 |
| **optimiser actually driving the parameters** | **COBYLA 47 (87%)**, L-BFGS-B 7 (13%) |
| mapping | Jordan–Wigner 36, parity 14, Bravyi–Kitaev 4 |
| orbitals | Hartree–Fock 35, CASSCF 19 |

The roadmap recorded this as "39/54 plain COBYLA (72%)". That undercounts it: ADAPT-VQE
runs an inner optimiser, and eight of the ten ADAPT entries run COBYLA inside. **87% of
the suite is optimised by COBYLA.**

Crossing ansatz with the optimiser that actually moves the parameters leaves a hole:

| | COBYLA | L-BFGS-B |
|---|---|---|
| ADAPT-VQE | 8 | 2 |
| hardware-efficient | 24 | 5 |
| UCCSD | 15 | **0** |

No entry in the suite pairs a structured, physically-motivated ansatz with a
gradient-based optimiser. Every claim the project makes about optimiser families rests on
seven entries, five of which are hardware-efficient — and two of those seven are the
entries that lose certification across machines
([`CROSS_MACHINE.md`](CROSS_MACHINE.md)).

## Filling the empty cell changes the numbers, not just the balance

Every one of the 15 UCCSD entries was regenerated with L-BFGS-B in place of COBYLA:
same molecule, same mapping, same active space, same orbitals, same tapering, one
variable changed.

| molecule | mapping | COBYLA gap | L-BFGS-B gap | improvement |
|---|---|---|---|---|
| C₄H₄ | Jordan–Wigner | 7.917 mHa | 0.0000001 mHa | ×74,000 |
| H₄ | Jordan–Wigner | 2.222 mHa | 0.052 mHa | ×42 |
| NH₃ | Jordan–Wigner | 0.032 mHa | 0.012 mHa | ×2.8 |
| BeH₂ | Jordan–Wigner | 0.0067 mHa | 0.00008 mHa | ×85 |
| LiH | Jordan–Wigner | 0.0029 mHa | 0.0000025 mHa | ×1,100 |
| water dimer | Jordan–Wigner | 0.0019 mHa | 0.000024 mHa | ×80 |
| BeH₂ | parity | 0.0024 mHa | 0.0000003 mHa | ×7,800 |
| H₂O | Jordan–Wigner | 0.00014 mHa | 0.000034 mHa | ×4 |
| H₂, HF (6 entries) | all three | already exact | exact | — |

**The gradient-based run is better on all 14 pairs and worse on none.** Twelve of the
fourteen land below one microhartree, against seven of the fourteen for COBYLA. The whole
set took ninety seconds of wall time on 5 cores.

## What that means, and it is not a tidiness argument

For the UCCSD entries, **the published gap is a measurement of COBYLA's convergence, not
of the ansatz.** C₄H₄ is the extreme case: the entry certifies at 7.9 mHa, close to the
10 mHa bar, and reads as a hard problem near the edge of what UCCSD can do. It is not.
The same ansatz on the same Hamiltonian reaches 10⁻¹⁰ Ha when the optimiser can use
gradients. The 7.9 mHa is the optimiser giving up.

That has three consequences worth stating plainly.

**The benchmark is partly measuring the wrong thing.** A reader comparing UCCSD against
the hardware-efficient ansatz across the suite is, for those entries, comparing COBYLA on
UCCSD against COBYLA on a hardware-efficient circuit. The ansatz comparison is confounded
with an optimiser that struggles as parameter count grows — 152 parameters for C₄H₄, 64
for H₄.

**It probably explains a cross-machine result.** C₄H₄ Jordan–Wigner UCCSD is one of the
two entries flagged **marginal**: it moved 6.0 mHa between machines, three times its
margin. An optimiser stopping early on a flat landscape is exactly the configuration
where last-bit differences choose a different stopping point. The gradient-based
counterpart converges to 10⁻¹⁰ Ha, where there is no room left to move.

**It is cheap.** Ninety seconds bought a 74,000-fold accuracy improvement on the entry
that most looked like a physics limit.

## ADAPT-VQE: the optimiser is not the limit, the stopping rule is

The same experiment on ADAPT-VQE gives the opposite answer, and a more uncomfortable one.
Eight of the ten ADAPT entries ran COBYLA inside; regenerating them with L-BFGS-B changes
almost nothing:

| molecule | COBYLA inner | L-BFGS-B inner | change | operators |
|---|---|---|---|---|
| C₄H₄ | 5.96340 mHa | 5.96340 mHa | 0 | 2 → 2 |
| benzene | 9.53971 mHa | 9.53972 mHa | +0.00001 | 11 → 11 |
| N₂ | 8.83061 mHa | 8.82312 mHa | −0.0075 | 25 → 25 |
| H₆ | 9.27283 mHa | 9.75511 mHa | +0.482 | 28 → 28 |
| H₄, C₄H₆, H₂CO, water dimer | — | — | under 0.0001 | unchanged |

Better on five, worse on three, every difference negligible beside the UCCSD result, and
the same operators selected every time. **ADAPT's accuracy is not limited by its inner
optimiser.** It optimises 1 to 28 parameters at a time, where COBYLA is perfectly
adequate; UCCSD optimises 56 to 404 at once, where it is not. The discriminator is the
parameter count, not the ansatz family.

But that is not why those numbers are what they are. **Every ADAPT entry in the suite
stops the moment it certifies.** `early_stopped` is true for all ten, and it shows in the
gaps: H₄ 9.94, benzene 9.54, H₆ 9.27, H₈ 9.80, H₁₀ 9.98 mHa — a cluster just under the
10 mHa bar, which is not what an ansatz limit looks like. It is what a stopping rule looks
like.

Re-running with the rule disabled:

| molecule | published (stops at the bar) | run to convergence | improvement |
|---|---|---|---|
| H₄ | 9.9417 mHa, 1 operator | 0.0514 mHa, 22 operators | ×193 |
| C₄H₆ | 2.8286 mHa, 1 operator | 0.00033 mHa, 9 operators | ×8,500 |
| H₂CO | 1.1239 mHa, 1 operator | 0.00395 mHa, 7 operators | ×285 |

H₄ certifies with a **single** operator at 9.94 mHa and stops there. Twenty-two operators
reach 0.05 mHa.

## What the two halves add up to

For the UCCSD entries the published gap measures COBYLA's convergence. For the ADAPT
entries it measures where the stopping rule fired. **In neither case does it measure what
the ansatz can do**, which is what a reader comparing the two families on the leaderboard
would reasonably assume it means.

Stopping at the smallest certifying circuit is a defensible design — it answers "what is
the cheapest circuit that certifies this molecule", which is a real question. The problem
is that the answer is then reported in the same column, and ranked against, numbers
produced by running an optimiser as far as it will go. An ADAPT entry at 9.94 mHa and a
UCCSD entry at 0.0001 mHa are not two points on one scale.

It also connects to the machine-dependence result. A run that halts on "is this attempt
good enough" is halting on a comparison of near-equal numbers, which is exactly the
mechanism that makes an entry move between machines
([`CROSS_MACHINE.md`](CROSS_MACHINE.md)). Every ADAPT entry stops that way, and so do the
multistart hardware-efficient entries that lost certification.

## Proposed, not done

1. **Add the 15 gradient-based UCCSD entries** as new entries rather than replacements.
   The COBYLA ones are published and cited; they stay, and the pair becomes the evidence
   for the optimiser claim rather than a single-armed assertion.
2. **Rebalance by addition, not deletion.** Nothing published is withdrawn. The suite
   grows from 54 toward a table with no empty cells.
3. **DONE, staged.** ADAPT now covers all 16 molecules: the six that had none — BeH₂,
   H₂, H₂O, HF, LiH, NH₃ — were generated with both inner optimisers, so those cells
   arrive paired. All certify.
4. **Report the stopping rule, or stop applying it.** The choice is between recording
   `early_stopped` visibly on the leaderboard so a 9.94 mHa entry is read as "stopped at
   the bar with one operator" rather than as an accuracy limit, or running ADAPT to
   convergence and reporting the cheapest certifying circuit as a separate column. The
   second is more work and answers both questions. This is the decision worth taking to
   the co-author.
5. **Consider the N₂ layer scan.** Five of the 29 hardware-efficient entries are N₂ at
   different depths, and two of the three fragile entries in the suite are N₂
   hardware-efficient. Depth scans are useful, but five entries of one molecule and one
   ansatz is a large share of a 54-entry suite.

**None of this can merge until the paper is out.** Adding entries changes the per-molecule
best in Table 2, the certified count, and the leaderboard composition, all of which the
draft cites. The candidates are staged and reproducible so that the merge is a decision
rather than a re-run.
