# The noisy tier: what every certified circuit loses on a device

Every certified QEncode entry is an exact statevector result. That is the right way to
measure an *algorithm*: the ansatz, the optimiser, the encoding, with no device error at
all. It is not what a device returns. This document describes the measurement that
answers the second question for every published entry that can be simulated exactly, how
the answer is reported on the leaderboard, what it does not establish, and two things
about the published entries that the measurement exposed.

It supersedes [`GATE_NOISE.md`](GATE_NOISE.md), which probed ten hardware-efficient entries
and reached the right qualitative conclusion with one wrong constant and one over-claim,
both corrected there in place. Tool: `tools/noisy_tier.py`. Records:
`experiments/noisy_tier/records/`, one JSON per entry, hashed in
`experiments/MANIFEST.json`. Tests: `tests/test_noisy_tier.py`.

---

## Why a measurement track and not a second certification

When gate noise was first probed the finding was that, at error rates near current
superconducting hardware, every multi-qubit entry moves by more than the 10 mHa threshold.
A pass/fail "noisy tier" would therefore mark everything failed, which is true and tells a
reader nothing. What discriminates between entries is **how much** is lost, how that
compares with the circuit's size, and whether the standard mitigation recovers it. So the
noisy tier is a set of measured numbers next to each entry, not a status. No entry's tier,
rank or hash depends on it, and the rules amendment that introduced it says so
([`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md), 2026-09-04).

---

## The measurement

For each entry at or below 10 tapered qubits:

1. **Rebuild the circuit with the pipeline's own builders.** HEA, tapered UCCSD or ADAPT,
   with the stored optimal parameters and, for ADAPT, the stored operator selection.
   The Hamiltonian is taken from the entry's own serialised Pauli terms (see *Rebuild
   discipline* below for why); the tapered Hartree–Fock state from the entry.
2. **Gate the rebuild.** The noiseless energy of the rebuilt circuit on the pipeline's
   statevector device must reproduce the stored energy to 10⁻⁶ Ha, or the entry is recorded
   as failed with the reason and nothing else is reported for it. Every measured record
   reproduces to 10⁻¹³ Ha or better except the CASSCF entries, which reproduce to 10⁻⁷.
3. **Decompose to a fixed gate set** — RX, RY, RZ, H, X, Y, Z, S, T, phase shift, CNOT, CZ —
   so that "a gate" means the same thing for every ansatz. Exponentials of sums of
   commuting Pauli words are split into products first (exact; commutation is verified
   for every pair). State preparation is treated as noiseless, consistent with the
   `circuit_stats` counts.
4. **Gate the decomposition.** The decomposed circuit, run as a density matrix with no
   noise, must reproduce the statevector energy to 10⁻⁸ Ha.
5. **Insert a named noise model's channels after every gate** and evaluate the energy of
   the noisy state. The models are those in `tools/noise_models.py`; they are complete
   specifications, not knobs. No sampling is involved anywhere: the result is one
   deterministic number per (entry, model).
6. **Zero-noise extrapolation** under `depolarizing-current/v1`: the circuit is evaluated
   with every channel applied λ = 1, 2 and 3 times in succession — the mixed-state
   analogue of gate folding, and exact, since composing depolarizing channels is again a
   depolarizing channel — and a quadratic polynomial through the three points is
   evaluated at λ = 0 (Richardson: 3E₁ − 3E₂ + E₃). The linear two-point value is
   recorded too.

### What each record contains, per model

| field | meaning |
|---|---|
| `penalty_mHa` | E_noisy − E_certified. The hardware penalty. |
| `noisy_gap_mHa` | E_noisy − E_exact. Never negative: Tr(ρH) ≥ λ_min for any state, and the tapered sector's minimum is the exact ground energy. Checked per record. |
| `meets_threshold_under_noise` | noisy gap < 10 mHa. |
| `eps_model` | The probability that **at least one** depolarizing event happened anywhere in the circuit (pure depolarizing models only). Exact, from the decomposed gate counts. |
| `eps_eff` | penalty / (c_I − E): the measured fraction of the way from the certified energy to the maximally mixed energy c_I = Tr(H)/2ⁿ. |
| `eps_ratio` | eps_eff / eps_model — how much of the way to full mixing an average error event actually carries the energy. |
| `bound_mHa` | eps_model · (λ_max − E). A rigorous upper bound on the penalty; holds in every record. |
| `full_mixing_estimate_mHa` | eps_model · (c_I − E). The estimate that assumes every error event fully mixes the register. Not a bound. |

and a `zne` block with the three energies, both extrapolations, the residual against the
certified energy and whether the extrapolated gap is under the bar.

---

## The mathematics, and where the earlier material went wrong

**Convention.** PennyLane's `DepolarizingChannel(p)` is

    ρ → (1 − p) ρ + (p/3)(XρX + YρY + ZρZ) = (1 − 4p/3) ρ + (4p/3) · I/2

because XρX + YρY + ZρZ = 2·Tr(ρ)·I − ρ. The probability that the channel replaces its
qubit by the maximally mixed state is therefore **q = 4p/3, not p**. A two-qubit gate
carries one such channel on each of its wires. For N₁ one-qubit and N₂ two-qubit gates the
probability that no event happened anywhere is (1 − q₁)^N₁ (1 − q₂)^(2N₂), so

    ε = 1 − (1 − 4p₁/3)^N₁ · (1 − 4p₂/3)^(2N₂).

The first probe used (1 − p) in place of (1 − 4p/3), understating ε by 4/3 per channel.
The check that fixes the convention is the single-gate, single-qubit entries: with one
gate on one qubit any error event mixes the whole register, so the penalty must equal
ε·(c_I − E) *exactly*, and it does (H₂ JW UCCSD: 0.386 mHa measured, 0.386 predicted).
Under the old convention the prediction would be three quarters of the measurement. This
is pinned by `test_single_gate_single_qubit_penalty_is_exactly_the_full_mixing_estimate`
and `test_depolarizing_channel_convention_is_four_thirds`.

**Bound versus estimate.** The total channel is a convex mixture of "no event anywhere"
(probability 1 − ε, in which the state is exactly the ideal one, because each channel is
(1 − q)·id + q·(replace by I/2) and the identity branch commutes with the unitaries) and
"at least one event" (probability ε, some density matrix σ). Hence

    E_noisy = (1 − ε) E + ε Tr(σH)      ⇒      E_noisy − E ≤ ε (λ_max − E).

That inequality is the bound, and nothing more can be said without knowing σ. Replacing σ
by I/2ⁿ gives ε·(c_I − E), which the earlier document called "a reliable upper bound". It
is neither reliable as a bound nor an upper one in general; it is the value the penalty
would take if every error event fully mixed the register. The measured ratio eps_eff/ε
says how far from that a real circuit is.

**Gate counts are the decomposed circuit's**, because those are the gates the channels
follow. They differ from `circuit_stats`, which counts the untapered standard
decomposition: an entry's `ansatz_num_2q_gates` and the `n_2q` in its record are
different quantities and should not be compared.

**Extrapolation axis.** Composing λ copies of `DepolarizingChannel(p)` equals one channel
with 1 − 4p'/3 = (1 − 4p/3)^λ (`test_channel_composition_scaling_equals_closed_form`), so
"noise scale λ" is exact, not a linearised p → λp. Richardson extrapolation is then a
polynomial in λ through three exact points. Where ε at λ = 1 is already large the energy
is nowhere near polynomial in λ and the extrapolation is meaningless; the records show
this rather than hiding it.

---

## Results

`depolarizing-current/v1` is depolarizing after every gate at 1q 5×10⁻⁴, 2q 5×10⁻³
(near good current superconducting devices); `opt` is 1×10⁻⁴ / 1×10⁻³, `pess` 1×10⁻³ /
1×10⁻², `device-sc` adds amplitude and phase damping at 10⁻³. Penalties in mHa; the
certification bar is 10 mHa. "gap" is the certified noiseless gap. "ε_eff/ε" is under the
current model. "after ZNE" is whether the Richardson-extrapolated gap is under the bar.
HEA depth is `r`. (Two legend marks used here before the 2026-09-07 sector fix are gone
with the fault they described: no entry now has a constant tapered Hamiltonian, and no
entry carries a constant correction.)

The table is generated from the records by `python tools/noisy_tier.py --table`;
`tests/test_noisy_tier.py` fails if this copy and the records disagree.

<!-- TABLE:BEGIN -->
| entry | q | 1q | 2q | gap | opt | **current** | pess | device-sc | ε_eff/ε | ZNE resid. | under noise | after ZNE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H2 BK HEA r2 | 1 | 3 | 0 | 0.000 | 0.2 | **1.2** | 2.3 | 4.6 | 1.00 | +0.00 | yes | yes |
| H2 JW HEA r2 | 1 | 3 | 0 | 0.000 | 0.2 | **1.2** | 2.3 | 4.6 | 1.00 | +0.00 | yes | yes |
| H2 PAR HEA r2 | 1 | 3 | 0 | 0.000 | 0.2 | **1.2** | 2.3 | 4.6 | 1.00 | +0.00 | yes | yes |
| H2 BK UCCSD | 1 | 1 | 0 | 0.000 | 0.1 | **0.4** | 0.8 | 1.5 | 1.00 | +0.00 | yes | yes |
| H2 JW UCCSD | 1 | 1 | 0 | 0.000 | 0.1 | **0.4** | 0.8 | 1.5 | 1.00 | +0.00 | yes | yes |
| H2 PAR UCCSD | 1 | 1 | 0 | 0.000 | 0.1 | **0.4** | 0.8 | 1.5 | 1.00 | +0.00 | yes | yes |
| HF BK HEA r2 | 1 | 3 | 0 | 0.000 | 0.3 | **1.4** | 2.8 | 5.7 | 1.00 | +0.00 | yes | yes |
| HF JW HEA r2 | 1 | 3 | 0 | 0.000 | 0.3 | **1.4** | 2.8 | 5.7 | 1.00 | +0.00 | yes | yes |
| HF PAR HEA r2 | 1 | 3 | 0 | 0.000 | 0.3 | **1.4** | 2.8 | 5.7 | 1.00 | +0.00 | yes | yes |
| HF BK UCCSD | 1 | 1 | 0 | 0.000 | 0.1 | **0.5** | 0.9 | 1.9 | 1.00 | +0.00 | yes | yes |
| HF JW UCCSD | 1 | 1 | 0 | 0.000 | 0.1 | **0.5** | 0.9 | 1.9 | 1.00 | +0.00 | yes | yes |
| HF PAR UCCSD | 1 | 1 | 0 | 0.000 | 0.1 | **0.5** | 0.9 | 1.9 | 1.00 | +0.00 | yes | yes |
| BeH2 JW HEA r2 | 3 | 9 | 4 | 0.000 | 6.9 | **34.4** | 67.9 | 45.4 | 0.47 | +0.04 | no | yes |
| BeH2 PAR HEA r2 | 3 | 9 | 4 | 0.000 | 6.9 | **34.4** | 67.9 | 45.4 | 0.47 | +0.04 | no | yes |
| BeH2 JW UCCSD | 3 | 54 | 32 | 0.007 | 57.9 | **263.1** | 468.9 | 320.1 | 0.56 | +13.75 | no | no |
| BeH2 PAR UCCSD | 3 | 110 | 64 | 0.002 | 112.2 | **466.4** | 755.1 | 556.3 | 0.61 | +71.40 | no | no |
| C4H6 JW ADAPT | 4 | 10 | 12 | 2.829 | 16.2 | **77.8** | 148.4 | 94.0 | 0.51 | +0.86 | no | yes |
| H2CO JW ADAPT | 4 | 14 | 8 | 1.124 | 16.9 | **81.7** | 156.4 | 99.1 | 0.51 | +0.68 | no | yes |
| H2O JW HEA r2 | 4 | 12 | 6 | 0.403 | 10.9 | **53.7** | 106.0 | 72.7 | 0.34 | +0.05 | no | yes |
| H2O PAR HEA r2 | 4 | 12 | 6 | 0.399 | 18.7 | **91.4** | 177.9 | 115.2 | 0.58 | +0.33 | no | yes |
| H2O JW UCCSD | 4 | 170 | 120 | 0.000 | 238.4 | **893.4** | 1331.9 | 1027.9 | 0.58 | +253.17 | no | no |
| C4H4 PAR HEA r2 | 5 | 15 | 8 | 3.834 | 16.4 | **79.5** | 153.3 | 93.8 | 0.61 | +0.50 | no | yes |
| H4 JW ADAPT | 5 | 14 | 16 | 9.942 | 26.6 | **126.2** | 237.1 | 150.5 | 0.49 | +2.27 | no | no |
| H4 JW HEA r4 | 5 | 25 | 16 | 9.283 | 26.7 | **126.8** | 238.5 | 160.8 | 0.48 | +2.15 | no | no |
| H4 PAR HEA r4 | 5 | 25 | 16 | 4.492 | 27.4 | **130.3** | 245.4 | 160.9 | 0.49 | +2.12 | no | yes |
| H4 JW UCCSD | 5 | 713 | 576 | 2.222 | 670.8 | **1222.7** | 1292.5 | 1281.5 | 0.94 | +1091.28 | no | no |
| LiH JW HEA r2 | 5 | 15 | 8 | 0.096 | 17.7 | **87.2** | 171.6 | 119.8 | 0.25 | +0.18 | no | yes |
| LiH PAR HEA r2 | 5 | 15 | 8 | 3.370 | 19.4 | **95.6** | 187.8 | 131.2 | 0.27 | +0.23 | no | yes |
| LiH JW UCCSD | 5 | 662 | 560 | 0.003 | 1047.5 | **2719.7** | 3129.5 | 2995.6 | 0.85 | +1971.75 | no | no |
| NH3 JW HEA r2 | 5 | 15 | 8 | 1.880 | 13.8 | **67.3** | 130.4 | 84.3 | 0.42 | +0.37 | no | yes |
| NH3 PAR HEA r2 | 5 | 15 | 8 | 0.734 | 16.4 | **80.0** | 155.3 | 98.1 | 0.49 | +0.38 | no | yes |
| NH3 JW UCCSD | 5 | 713 | 576 | 0.032 | 671.6 | **1316.2** | 1439.3 | 1409.1 | 0.90 | +1093.14 | no | no |
| water_dimer JW ADAPT | 5 | 6 | 8 | 0.111 | 13.5 | **65.9** | 127.6 | 79.0 | 0.41 | +0.33 | no | yes |
| water_dimer JW HEA r2 | 5 | 15 | 8 | 0.332 | 12.7 | **62.5** | 122.6 | 83.0 | 0.37 | +0.14 | no | yes |
| water_dimer PAR HEA r2 | 5 | 15 | 8 | 0.114 | 16.6 | **81.0** | 157.0 | 102.1 | 0.48 | +0.39 | no | yes |
| water_dimer JW UCCSD | 5 | 657 | 528 | 0.002 | 578.8 | **1332.4** | 1490.3 | 1429.0 | 0.88 | +1044.32 | no | no |
| C4H4 JW ADAPT | 6 | 28 | 24 | 5.963 | 35.9 | **167.9** | 309.5 | 199.4 | 0.50 | +4.54 | no | no |
| C4H4 JW HEA r2 | 6 | 18 | 10 | 9.637 | 20.2 | **97.3** | 186.0 | 120.4 | 0.62 | +0.89 | no | no |
| C4H4 JW UCCSD | 6 | 2012 | 1664 | 7.917 | 990.7 | **1163.7** | 1166.9 | 1186.7 | 1.00 | +1157.44 | no | no |
| N2 JW ADAPT | 8 | 326 | 368 | 8.831 | 1608.7 | **3210.0** | 3416.3 | 3254.6 | 0.90 | +2868.97 | no | no |
| N2 JW HEA r10 | 8 | 88 | 70 | 4.513 | 318.1 | **1306.9** | 2093.2 | 1526.6 | 0.58 | +220.31 | no | no |
| N2 JW HEA r6 | 8 | 56 | 42 | 48.450 | 262.9 | **1127.8** | 1885.1 | 1324.1 | 0.70 | +126.63 | no | no |
| N2 JW HEA r4 | 8 | 40 | 28 | 138.646 | 131.4 | **601.2** | 1081.2 | 727.2 | 0.53 | +27.23 | no | no |
| N2 PAR HEA r4 | 8 | 40 | 28 | 103.522 | 116.0 | **540.2** | 990.5 | 633.4 | 0.47 | +16.42 | no | no |
| N2 PAR HEA r10 | 8 | 88 | 70 | 4.404 | 329.2 | **1352.9** | 2167.2 | 1575.8 | 0.60 | +227.36 | no | no |
| N2 JW UCCSD | 8 | 5108 | 5712 | 10.832 | 3559.5 | **3590.2** | 3590.3 | 3624.0 | 1.00 | +3590.23 | no | no |
| H6 JW ADAPT | 9 | 400 | 424 | 9.273 | 1112.9 | **2301.0** | 2536.6 | 2373.6 | 0.86 | +1909.93 | no | no |
| H6 JW HEA r4 | 9 | 45 | 32 | 105.377 | 119.9 | **542.7** | 963.3 | 648.9 | 0.57 | +29.25 | no | no |
| H6 JW HEA r10 | 9 | 99 | 80 | 27.256 | 298.6 | **1169.5** | 1783.4 | 1342.7 | 0.65 | +273.76 | no | no |
| benzene JW ADAPT | 9 | 154 | 176 | 9.540 | 611.0 | **1737.8** | 2069.4 | 1821.2 | 0.83 | +1147.70 | no | no |
| benzene JW HEA r6 | 9 | 63 | 48 | 127.956 | 170.5 | **719.1** | 1180.8 | 847.9 | 0.67 | +96.02 | no | no |
| benzene JW HEA r10 | 9 | 99 | 80 | 8.741 | 193.4 | **794.3** | 1276.7 | 936.7 | 0.51 | +135.29 | no | no |
<!-- TABLE:END -->

### What the numbers say

- **Under noise near current hardware no multi-qubit entry stays under the bar.** The
  smallest multi-qubit penalty is 34.4 mHa (BeH₂, HEA, 4 two-qubit gates — the same to
  three figures under Jordan–Wigner and parity, as it should be), the largest 3590 mHa
  (N₂ Jordan–Wigner UCCSD, 5712 two-qubit gates), where ε = 1.000 to three decimals: the
  state is maximally mixed and the energy is c_I. The only entries under the bar with
  noise are the twelve one-qubit H₂ and HF circuits, with one to three gates and no
  two-qubit gate. That is a statement about circuit size, not about robustness.
- **The penalty is set by the two-qubit gate count, and it saturates.** Along each
  molecule's entries the penalty tracks N₂; for the eight circuits above a few hundred
  two-qubit gates (the [4,4] and [6,6] UCCSD entries, N₂ and H₆ and benzene ADAPT) ε
  exceeds 0.85 and the penalty approaches c_I − E, so adding gates no longer adds penalty.
  N₂ UCCSD makes the point twice over: 5712 two-qubit gates after decomposition, against
  70 for the ten-layer hardware-efficient entry on the same molecule. UCCSD's certified
  gaps of a few µHa are bought with circuits that a device turns into a random state.
- **An error event carries the energy about half way to the mixed value** in shallow
  circuits (ε_eff/ε from 0.25 for LiH HEA to 0.62), and nearly all the way (0.83–1.00) in
  deep ones, where later gates spread each local error across the register. This is the
  quantitative form of the locality argument the first probe made, now against the correct
  ε.
- **Zero-noise extrapolation recovers the shallow circuits and not the deep ones.** For
  HEA and ADAPT circuits with up to 16 two-qubit gates (ε ≲ 0.2) the extrapolated
  residual is 0.04–2.3 mHa and the extrapolated gap is under the bar wherever the
  noiseless gap left room for it. Where it does not — H₄ JW HEA and ADAPT at 9.3 and
  9.9 mHa noiseless, C₄H₄ JW HEA at 9.6 — the failure after extrapolation is the thin
  certification margin, not the noise: the same entries the margin column already flags.
  Beyond that the residual grows with depth without interruption: 14 to 274 mHa for the
  circuits between 17 and 100 two-qubit gates, and 253 mHa to 3590 mHa above 100, where
  the three-point polynomial is extrapolating a curve that saturated long before λ = 1.
  At N₂ UCCSD the extrapolation returns the noisy energy unchanged to two decimals,
  because all three noise scales sit at the fully mixed value.
- **Depth is a trade-off the accuracy ranking cannot see.** N₂ HEA at 4, 6 and 10 layers
  certifies only at 10 layers (gap 4.5 mHa versus 48 and 139), and pays 1307 mHa for it
  against 601 at 4 layers. The leaderboard's hardware-cost tab ranks by two-qubit gates
  for this reason; the noisy tier puts a measured energy on the same axis.
- **Damping is not much worse than depolarizing here.** `device-sc/v1` adds amplitude and
  phase damping at 10⁻³ per gate on top of the current depolarizing rates and raises the
  penalty by 15–35%. Its asymmetry (relaxation toward |0⟩) does not change any conclusion
  above.

### What the leaderboard shows

One column, **Noise**: the `depolarizing-current/v1` penalty in mHa, green if the gap under
noise is still under the bar, blue if it is over but the extrapolated gap is under, plain
otherwise. Hovering gives the gap under noise, the extrapolated residual, and the model.
It is `—` for entries above 10 qubits (absent, not zero) and for the four
constant-Hamiltonian entries (not measurable, below). All 52 entries at or below 10 qubits
are measured; the two C₄H₄ CASSCF entries whose circuit only rebuilds under the kernel
they were generated with were measured on that machine (below). Export: `scripts/export_leaderboard_v4.py` reads
`experiments/noisy_tier/summary.json`; the CSVs and the database carry `noise_status`,
`noise_penalty`, `noisy_gap`, `zne_residual` and `noise_model`, in Ha like `gap` and
`margin`.

---

## Rebuild discipline: why the Hamiltonian comes from the entry

The first version of the tool re-derived every Hamiltonian through PySCF and Z₂ tapering,
exactly as `generate_entry_v4.main()` does, and then rebuilt the circuit on it. Every
entry with canonical Hartree–Fock orbitals passed the rebuild gate to 10⁻¹³ Ha. **Every
CASSCF entry failed it**, by 0.01 to 0.2 Ha — and yet `scripts/verify_entry.py` passes
those same entries at the same commit, and the verification sweep of 2026-08-27 passed all
54.

The two facts are consistent. A CASSCF energy is invariant under rotations inside the
active space, so the converged active orbitals are fixed only by the optimiser's path,
which is fixed by rounding. Re-deriving the Hamiltonian today lands in a different orbital
gauge: the coefficients differ from the stored ones by 3×10⁻⁵ Ha for N₂ (measured with
the pipeline's own serialiser, under 1 and under 64 BLAS threads alike; LiH with canonical
HF orbitals reproduces to 10⁻¹⁵). The cause was found later the same day and it is not
rounding on a different day: it is the BLAS kernel, which OpenBLAS selects by processor.
The generating run used the cluster's SkylakeX kernel; the workstation uses Haswell. With
the kernel forced to the same value, PySCF's output is bit-identical on both machines,
CASSCF included ([`CROSS_MACHINE.md`](CROSS_MACHINE.md)). Verification re-optimises the VQE from scratch, and
energies are gauge-invariant, so it passes. Rebuilding the **stored circuit with the
stored parameters** is not gauge-invariant: those parameters mean something only in the
orbital basis they were optimised in.

The tool therefore takes the tapered Hamiltonian from the entry's own `pauli_terms` — the
object that is hashed and certified — and the tapered HF state from the entry. The HEA
needs nothing else. The UCCSD and ADAPT operator pools depend only on the symmetry
structure of the untapered Hamiltonian (its Z₂ generators, Pauli-X operators and sectors),
not on the coefficients, so that structure is regenerated through PySCF and checked
against the stored sectors and HF state before the pool is built. Two consequences:

- **C₄H₄ UCCSD and ADAPT can be measured only on the machine that generated them.**
  Under the workstation's Haswell BLAS kernel the CASSCF gauge for cyclobutadiene exposes
  a third Z₂ symmetry (5 tapered qubits) where the generating run found two (6); the CASCI
  energy agrees to 2×10⁻¹⁰ Ha, so this is a symmetry-detection tolerance deciding, not the
  physics, and the pool for the stored 6-qubit gauge cannot be regenerated there. On the
  cluster, whose SkylakeX kernel is the one these two entries were generated with, the
  re-derived Hamiltonian matches the stored coefficients exactly (maximum deviation 0.0),
  the pipeline tapers to six qubits, and both entries rebuild to 3×10⁻¹³ Ha. **That is how
  the two published records were measured** (2026-09-09); their provenance names the
  machine, as every noisy-tier record now does. The two C₄H₄ HEA entries need no pool and
  are measured on either machine. The general statement is the one in
  [`CROSS_MACHINE.md`](CROSS_MACHINE.md): reusing a CASSCF entry's stored circuit is bound
  to the kernel it was generated under, and here that binding is visible as a whole qubit
  rather than as a last bit.
- **The stored parameters of a CASSCF entry are gauge-specific and the gauge is not
  stored.** `verify_entry.py` remains the right instrument for certification, because it
  re-optimises. Anything that wants to *reuse* a CASSCF entry's parameters — this tool,
  or a user warm-starting from a published entry — must take the Hamiltonian from the
  entry, not re-derive it. That is worth stating in the schema, and is recorded here
  until it is.

---

## What the measurement exposed

Two things came out of the rebuild gate that are about the published entries rather than
about noise. The first has since been fixed and the affected entries regenerated; the
second is a property of the schema that is now documented rather than changed.

### 1. The parity and Bravyi–Kitaev entries were tapered in the wrong sector — fixed 2026-09-07

Every one of the 13 entries with a non-Jordan–Wigner mapping (H₂ ×4, HF ×4, BeH₂ ×2,
N₂ ×2, NH₃ ×1) carries a field `bk_constant_correction_ha` of −0.30 to −0.76 Ha. The
pipeline computes it as *CASCI energy − ground energy of the tapered Hamiltonian* and,
when it exceeds 0.1 Ha, adds it to both the VQE energy and the exact reference before
computing the gap. The code calls this a "BK constant-offset correction (same as v3)",
on the understanding that PennyLane's tapering drops a constant for those mappings.

It does not. Tapering restricts H to one joint eigenspace of its Z₂ symmetries, and the
spectrum of the restriction is exactly the spectrum of H on that sector. A brute-force
scan over every sector (8 for H₂ and HF, 32 for BeH₂) shows the ground state is present
in a sector the pipeline did not choose:

| molecule, mapping | pipeline sector, tapered minimum | sector containing the ground state |
|---|---|---|
| H₂ parity and BK | [−1, −1, 1], −0.7205 Ha | [1, −1, 1], −1.1313 Ha = CASCI |
| HF parity | [−1, −1, 1], −99.5766 Ha | [1, −1, 1], −100.0195 Ha = CASCI |
| BeH₂ parity | [−1, −1, 1, 1, 1], −15.4692 Ha | [1, 1, 1, 1, 1], −15.7684 Ha = CASCI |

The sector is derived from the Hartree–Fock occupation, and the derivation is correct for
Jordan–Wigner, where the HF state is a computational basis state with the electrons in the
first orbitals. Under parity and Bravyi–Kitaev the HF state is a different bit string, so
the same derivation lands in a different sector. The "constant correction" then shifts a
wrong-sector energy until it matches CASCI.

At the time this was written the consequence was that those entries' gaps measured the
distance to the wrong sector's own minimum rather than to the molecular ground state, and
that the four one-qubit H₂ and HF parity entries had a tapered Hamiltonian consisting of a
single identity term — the VQE optimised nothing and their gap of exactly 0.000 mHa was
vacuous.

**This is fixed.** The sector is now derived from the Hartree–Fock state of the mapping
actually in use and verified against CASCI before anything is built on it, the "constant
correction" branch raises instead of shifting, and all 18 affected entries — 13 with the
wrong sector, plus 5 more that had the right sector but the wrong Hartree–Fock reference
state — were regenerated. No entry changed trust level. Full account, evidence and the
before/after table: [`SECTOR_FIX.md`](SECTOR_FIX.md). Superseded entries are kept in
`releases/v4/db_superseded/`.

The numbers in this document's results table are from the corrected suite. Nothing in the
noise measurement itself changed: the same tool, run against corrected entries.

### 2. CASSCF entries' stored parameters are gauge-specific

Described above under *Rebuild discipline*. Not a defect in any entry — every one of them
re-verifies — but a property the schema does not state and downstream users would not
guess.

---

## What this does not establish

- **A model, not a device.** Depolarizing and damping channels with uniform rates. No
  topology and no transpilation (a device needing SWAP networks is worse, likely much
  worse), no readout error, no crosstalk, no correlated or non-Markovian noise, no drift.
- **Ideal state preparation.** BasisState is noiseless, consistent with `circuit_stats`.
- **Zero-noise extrapolation as implemented is idealised.** The noise is scaled exactly and
  the energies are exact. On a device the folded circuits are longer, the extrapolation
  works on sampled estimates, and the residual is larger than here.
- **H₈ and H₁₀ are absent, not zero.** At 13 and 18 tapered qubits the density matrix has
  6.7×10⁷ and 6.9×10¹⁰ elements; the first is hours per evaluation, the second out of
  reach. Both are stated as absent on the leaderboard.
- **Nothing here is certified.** It is measured, from certified inputs, under a named model.

---

## Reproducing

```bash
python tools/noisy_tier.py --workers 12          # every entry <= 10 tapered qubits, resumable
python tools/noisy_tier.py --summarise           # -> experiments/noisy_tier/summary.{json,csv}
python tools/noisy_tier.py --table               # the table above
python tools/make_experiment_manifest.py         # re-hash the records into experiments/MANIFEST.json
python -m pytest tests/test_noisy_tier.py        # conventions, extrapolation, record consistency
```

The run is deterministic (no sampling, single-threaded BLAS pinned before NumPy loads).
On 64 cores with 12 workers the full sweep takes about 45 minutes; the deep UCCSD and
ADAPT circuits at 8–9 qubits dominate.
