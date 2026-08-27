# Gate noise: what a published entry would look like on hardware

Every certified QEncode entry is an exact statevector result. That is the right way to
measure an *algorithm*, and it is not what a device returns. This measures the difference,
by taking each published hardware-efficient entry, rebuilding its circuit from the optimal
parameters it recorded, and re-evaluating the same energy under named gate-noise models.

**Nothing in the suite changes.** No entry is modified, no hash is touched. Tools:
`tools/noise_models.py`, `tools/probe_gate_noise.py`.

---

## Why this is not more shot noise

The two are qualitatively different and the difference decides how results must be read.

**Shot noise is zero-mean.** More shots shrink it; the estimator is unbiased; averaging
converges to the right answer. That is what
[`SHOT_NOISE_AND_ALLOCATION.md`](SHOT_NOISE_AND_ALLOCATION.md) is about.

**Gate noise is a bias.** Every channel modelled here is dissipative and drives the state
toward the maximally mixed state, whose energy is the mean of the spectrum and therefore
above the ground state. Averaging does not remove it. It can only push the energy **up**,
and in every measurement below it does.

---

## The models

Named and versioned, because "depolarizing noise" is not a specification — it does not say
which channels act on which gates at what rates. Full definitions in
`tools/noise_models.py`; rates are per-gate error probabilities.

| name | 1q | 2q | channels |
|---|---|---|---|
| `ideal/v1` | — | — | none; the control, and what every published entry used |
| `depolarizing-opt/v1` | 1e-4 | 1e-3 | depolarizing — better than current hardware |
| `depolarizing-current/v1` | 5e-4 | 5e-3 | depolarizing — near good current superconducting devices |
| `depolarizing-pessimistic/v1` | 1e-3 | 1e-2 | depolarizing — ordinary devices |
| `device-sc/v1` | 5e-4 | 5e-3 | + amplitude and phase damping; asymmetric, relaxes toward \|0⟩ |

---

## Step 1: the reconstruction is verified before anything is claimed

The rebuilt noiseless circuit must reproduce the energy stored in the entry, or the
molecule is excluded rather than reported. Ten of twelve rebuild to 10⁻¹³ Ha or better.

**H₂ and HF do not, and were excluded.** Both are single-qubit after tapering with zero
two-qubit gates, and the generic hardware-efficient reconstruction used here does not
reproduce their published energies (off by 0.41 and 0.44 Ha).

**This is a fault in the reconstruction, not in the entries.** Both entries re-verify
cleanly through the pipeline — `scripts/verify_entry.py` reproduces each to within
10⁻⁶ Ha with the hash intact — so they are fully reproducible, and the one-qubit tapered
ansatz simply is not the generic layer structure this probe assumes. The gate did its job:
it excluded two molecules the probe would have reported wrongly, rather than averaging
them in.

A corollary worth stating: it also means gate-noise figures for H₂ and HF are *absent*
here, not zero.

---

## Step 2: the bias, on published results

Energy shift caused by noise, in mHa. Positive means noise pushed the energy up.
**The certification threshold is 10 mHa.**

| molecule | qubits | 2Q gates | noiseless gap | optimistic | current | pessimistic | device-sc |
|---|---|---|---|---|---|---|---|
| BeH₂ | 3 | 4 | 0.000 | 6.9 | **34.4** | 67.9 | 45.4 |
| H₂O | 4 | 6 | 0.403 | 10.9 | **53.7** | 106.0 | 72.7 |
| LiH | 5 | 8 | 0.096 | 17.7 | **87.2** | 171.6 | 119.8 |
| NH₃ | 5 | 8 | 1.880 | 13.8 | **67.3** | 130.4 | 84.3 |
| water dimer | 5 | 8 | 0.332 | 12.7 | **62.5** | 122.6 | 83.0 |
| H₄ | 5 | 16 | 9.283 | 26.7 | **126.8** | 238.5 | 160.8 |
| C₄H₄ | 6 | 10 | 9.637 | 20.2 | **97.3** | 186.0 | 120.4 |
| N₂ | 8 | 70 | 4.513 | 318.1 | **1306.9** | 2093.2 | 1526.6 |
| H₆ | 9 | 32 | 105.377 | 119.9 | **542.7** | 963.3 | 648.9 |
| benzene | 9 | 48 | 127.956 | 170.5 | **719.1** | 1180.8 | 847.9 |

### The headline

**At error rates near current hardware, every certified entry would fail certification on
a device.** The smallest penalty is 34 mHa on BeH₂, against a 10 mHa threshold and a
noiseless gap of essentially zero. N₂ moves by 1307 mHa — 290× the threshold, and 130,000×
its own noiseless gap of 4.5 mHa.

Even at rates *better than any current device*, only BeH₂ (6.9 mHa) stays under the
threshold, and only just.

This is not a criticism of the suite. It is a statement of what the suite currently
measures — algorithmic quality in the absence of device error — and it quantifies the gap
to the other thing people often assume it measures.

### Cost scales with two-qubit gates, as expected

N₂ carries 70 two-qubit gates because its certified configuration uses ten ansatz layers,
and it pays the largest penalty by a wide margin. The accuracy-vs-cost trade-off already on
the leaderboard becomes much sharper under noise: a deep circuit that wins on gap loses
badly once error is charged for.

---

## Step 3: can the penalty be predicted without a 4ⁿ simulation?

Density-matrix simulation costs 4ⁿ rather than 2ⁿ. Benzene at 9 qubits takes about 5
seconds per point; 13 qubits would take hours, and the 18-qubit H₁₀ entry is out of reach
entirely. So a formula would be worth having.

**Derived, not fitted.** Depolarizing noise takes ρ toward (1−ε)|ψ⟩⟨ψ| + ε·**I**/2ⁿ, so

```
ΔE  =  ε · ( Tr(H)/2ⁿ  −  E )        with   ε ≈ 1 − (1−p₁)^N₁q · (1−p₂)^(2·N₂q)
```

and `Tr(H)/2ⁿ` is exactly the **identity coefficient** of the Pauli decomposition, because
every other Pauli string is traceless. Every quantity is already stored in a published
entry. No free parameters.

**Result: it is a reliable upper bound, not an equality.** Measured / predicted across all
30 cells is **0.32 to 0.84, median 0.62** — always below 1, so it never under-states the
penalty.

It over-predicts for a physical reason. The derivation assumes the state moves toward the
*globally* maximally mixed state, but a single-qubit depolarizing channel only mixes the
qubit it acts on. Pauli terms with small support therefore survive better than the global
model allows, and the true shift is smaller. A tighter formula would have to track each
term's support through the circuit.

**Useful as a screen.** If the upper bound already exceeds the threshold by a wide margin —
as it does for every entry here — no simulation is needed to know the answer. A simple
`ΔE ≈ 0.6 × ε × (c_I − E)` reproduces the measured penalty to about ±35% across four
orders of magnitude in circuit size, which is enough for planning.

---

## The size ceiling, measured

| qubits | density-matrix dimension | time per energy evaluation |
|---|---|---|
| 3–6 | ≤ 4096 | under 0.1 s |
| 8 (N₂) | 65,536 | ~2 s |
| 9 (H₆, benzene) | 262,144 | ~5 s |
| 13 (H₈ tapered) | 67 M | minutes to hours |
| 18 (H₁₀ tapered) | 69 G | not feasible |

Exact noisy simulation is available for most of the suite and unavailable for the largest
entries. That is another reason the predictive formula matters.

---

## What this does not establish

- **Depolarizing and damping channels are a model**, not a device. Real hardware has
  correlated errors, crosstalk, drift, leakage and readout error, none of which are here.
- **No transpilation to a real topology.** Gate counts are the logical circuit's, so a
  device requiring SWAP networks would be worse, likely much worse.
- **No error mitigation.** Zero-noise extrapolation and similar techniques exist precisely
  to reduce this bias, and none is applied.
- **Hardware-efficient entries only.** UCCSD and ADAPT circuits cannot be rebuilt from the
  stored fields, so they are absent.
- **H₂ and HF are absent, not zero.** The probe cannot rebuild their one-qubit
  tapered circuit; both entries themselves verify cleanly through the pipeline.

---

## What this suggests next

Not a "Noisy-Sim" certified tier yet. The finding is that noise moves every entry by far
more than the threshold, so a naive noisy tier would simply mark everything as failing,
which is true but not informative.

More useful, in order:

1. **Publish the predicted hardware penalty per entry** as a derived column, the way T-gate
   estimates already are. It costs nothing, it is computable from stored fields, and it
   turns "this entry is certified" into "this entry is certified, and here is what it
   would cost on a device".
2. **Teach the probe the one-qubit tapered ansatz**, so H₂ and HF can be included.
   This is a limitation of the probe, not of the entries, which verify cleanly.
3. **Only then** consider a noisy tier, with error mitigation included, since without it
   the tier has no discrimination.

---

## Reproducing

```bash
python tools/probe_gate_noise.py              # all reconstructable HEA entries
python tools/probe_gate_noise.py H2O LiH N2   # selected molecules
python -c "import sys; sys.path.insert(0,'tools'); import noise_models; print(noise_models.names())"
```
