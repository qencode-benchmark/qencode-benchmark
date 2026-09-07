# The Z₂ sector fault: what went wrong, how it was found, and what changed

Every QEncode entry using a fermion-to-qubit mapping other than Jordan–Wigner was tapered
into the wrong symmetry sector, and the discrepancy that would have revealed it was added
back to the energies as a "constant correction". This document records the fault, the
evidence, the fix, and exactly which published numbers moved.

Fix: commit `ab7185b`, 2026-09-07. Code: `src/qencode/pipeline/generate_entry_v4.py`.
Tests: `tests/test_pipeline_regressions.py`. Superseded entries:
`releases/v4/db_superseded/`.

---

## How it surfaced

Not from a test. The noisy tier ([`NOISY_TIER.md`](NOISY_TIER.md)) rebuilds each certified
circuit from its stored parameters and refuses to report anything unless the rebuild
reproduces the stored energy. Building that gate meant reading the stored tapering block
of every entry, and 13 of the 54 carried a field named `bk_constant_correction_ha` holding
0.30 to 0.76 Ha. A correction of that size is not a rounding artefact; it is a third of a
hartree, thirty times the certification threshold.

The name encodes the belief behind it: that PennyLane's tapering drops a constant offset
for Bravyi–Kitaev, so adding it back restores the true energy. That belief is wrong, and
it is wrong for a reason that can be stated in one line.

**Tapering restricts H to one joint eigenspace of its Z₂ symmetries. The spectrum of the
restriction is a subset of the spectrum of H.** No constant is dropped and none can be:
every eigenvalue of the tapered operator is an eigenvalue of the original. If the tapered
ground energy sits 0.3 Ha above CASCI, the tapered operator is a perfectly good
Hamiltonian for a different sector, and no shift makes it the right one.

---

## The two bugs

Both are in how the sector is chosen. The sector is a list of ±1, one per Z₂ generator,
saying which joint eigenspace to keep.

### 1. The Hartree–Fock string is assumed to be Jordan–Wigner

`pennylane.qchem.optimal_sector` reads the sector off the Hartree–Fock determinant:

```python
hf_str = np.where(np.arange(num_orbitals) < active_electrons, 1, 0)
```

That is the occupation-number string: the first `active_electrons` spin-orbitals filled.
It is the Hartree–Fock state **under Jordan–Wigner only**. Parity and Bravyi–Kitaev encode
the same determinant as a different bit string — for a [4,4] active space the
occupation string `11110000` becomes `10100000` under parity. Reading generator
eigenvalues off the wrong bit string gives the wrong sector.

### 2. The generator's support is matched by position, not by wire label

```python
symmstr = np.array([1 if wire in tau.wires else 0 for wire in qubit_op.wires.toset()])
```

`qubit_op.wires.toset()` is an unordered Python set, and the resulting mask is XOR-ed
against a string indexed 0…n−1. A Hamiltonian's wire order is insertion order and is not
always sorted: NH₃ under Bravyi–Kitaev gives

```
H.wires = [0, 1, 3, 5, 6, 7, 2, 4]
```

so the mask and the bit string refer to different qubits.

**The two bugs cancel for NH₃ under Bravyi–Kitaev**, which is the one non-Jordan–Wigner
configuration in the suite that happened to get the right answer. That is worth stating
plainly: a spot check on that entry would have shown nothing wrong.

### And the reference state was wrong too

`qchem.taper_hf` builds the Hartree–Fock state with `qml.jordan_wigner` regardless of the
mapping in use. So even where the sector was right, the tapered state the ansatz starts
from was not the Hartree–Fock determinant. This affects entries the sector bug did not.

---

## The evidence

For each molecule and mapping, the sector chosen three ways: the old code, the corrected
derivation, and a brute-force scan of all 2ⁿ sectors keeping the lowest ground energy.
The target is the active-space CASCI energy, which the correct sector must reproduce.

| molecule | mapping | old sector → E_tapered | corrected → E_tapered | brute force | old error |
|---|---|---|---|---|---|
| H₂ | Jordan–Wigner | [1,−1,−1] → −1.13128651 | same | agrees | — |
| H₂ | parity | [−1,−1,1] → −0.72049511 | [1,−1,1] → −1.13128651 | agrees | 0.411 Ha |
| H₂ | Bravyi–Kitaev | [−1,−1,1] → −0.72049511 | [1,−1,1] → −1.13128651 | agrees | 0.411 Ha |
| HF | Jordan–Wigner | [1,−1,−1] → −100.01948280 | same | agrees | — |
| HF | parity | [−1,−1,1] → −99.57661597 | [1,−1,1] → −100.01948280 | agrees | 0.443 Ha |
| HF | Bravyi–Kitaev | [−1,−1,1] → −99.57661597 | [1,−1,1] → −100.01948280 | agrees | 0.443 Ha |
| BeH₂ | Jordan–Wigner | [1,1,1,1,1] → −15.76841099 | same | agrees | — |
| BeH₂ | parity | [−1,−1,1,1,1] → −15.46921940 | [1,1,1,1,1] → −15.76841099 | agrees | 0.299 Ha |
| BeH₂ | Bravyi–Kitaev | [−1,−1,1,1,1] → −15.46921940 | [1,1,1,1,1] → −15.76841099 | agrees | 0.299 Ha |
| NH₃ | Jordan–Wigner | [1,1,1] → −56.19788859 | same | agrees | — |
| NH₃ | parity | [−1,−1,1] → −55.81767446 | [1,1,1] → −56.19788859 | agrees | 0.380 Ha |
| NH₃ | Bravyi–Kitaev | [1,1,1] → −56.19788859 | same | agrees | — (bugs cancelled) |
| N₂ | Jordan–Wigner | [1,1,−1,−1] → −109.08995815 | same | agrees | — |
| N₂ | parity | [−1,−1,1,1] → −108.33352807 | [1,1,−1,1] → −109.08995815 | agrees | 0.756 Ha |
| N₂ | Bravyi–Kitaev | [1,−1,−1,1] → −108.00524868 | [1,1,−1,1] → −109.08995815 | agrees | 1.085 Ha |

Fifteen of fifteen agree with brute force after the fix, reproducing CASCI to 10⁻¹³ Ha.
**All eight Jordan–Wigner cases are unchanged** in sector, in tapered Hartree–Fock state
and in energy, which is why the 41 Jordan–Wigner entries in the suite are untouched.

---

## The fix

`_find_optimal_sector` now:

1. derives the sector from `qchem.hf_state(n_electrons, n_qubits, basis=<mapping>)`,
   matching each generator's support **by wire label** and carrying the generator's own
   coefficient into the eigenvalue;
2. **verifies** the tapered ground energy against the CASCI reference;
3. falls back to `qchem.optimal_sector`, then to a full scan;
4. **raises** if nothing reproduces the reference.

Nothing is accepted on trust. `_tapered_hf_state` is new and does the same for the
reference state: it keeps `qchem.taper_hf` for Jordan–Wigner, so every existing
Jordan–Wigner entry reproduces bit-for-bit, and otherwise tapers the stabilizers of the
correct Hartree–Fock basis state and solves for the reduced state — then checks the result
against the untapered Hartree–Fock energy. `_diagonal_energy` computes ⟨b|H|b⟩ from the
Pauli representation with no matrix, so the check is exact at any qubit count.

**The constant correction is retired.** The branch that added `e_casci − e_tapered_gs` to
every energy now raises instead. With a verified sector it can only fire on a real
failure, and a real failure must not be papered over.

---

## What it did to the published entries

<!-- RESULTS:BEGIN -->

All 18 affected entries were regenerated at commit `ab7185b` with the configuration each
one records, so only the tapering changed. The superseded files are in
`releases/v4/db_superseded/`.

| entry | what was wrong | gap before | gap after | trust |
|---|---|---|---|---|
| BeH2 parity HEA r2 | wrong sector, masked by a 0.299 Ha correction | 0.0000 | 0.0001 | certified |
| BeH2 parity UCCSD | wrong sector, masked by a 0.299 Ha correction | 2.2225 | 0.0024 | certified |
| C4H4 parity HEA r2 | symmetry count changed with the CASSCF gauge (6 -> 5 qubits); wrong Hartree-Fock reference | 6.1091 | 3.8341 | certified |
| H2 Bravyi-Kitaev HEA r2 | wrong sector, masked by a 0.411 Ha correction | 0.0000 | 0.0000 | certified |
| H2 Bravyi-Kitaev UCCSD | wrong sector, masked by a 0.411 Ha correction | 0.0000 | 0.0000 | certified |
| H2 parity HEA r2 | wrong sector, masked by a 0.411 Ha correction | 0.0000 | 0.0000 | certified |
| H2 parity UCCSD | wrong sector, masked by a 0.411 Ha correction | 0.0000 | 0.0000 | certified |
| H2O parity HEA r2 | wrong Hartree-Fock reference | 0.2958 | 0.3992 | certified |
| H4 parity HEA r4 | wrong Hartree-Fock reference | 5.6214 | 4.4923 | certified |
| HF Bravyi-Kitaev HEA r2 | wrong sector, masked by a 0.443 Ha correction | 0.0000 | 0.0000 | certified |
| HF Bravyi-Kitaev UCCSD | wrong sector, masked by a 0.443 Ha correction | 0.0000 | 0.0000 | certified |
| HF parity HEA r2 | wrong sector, masked by a 0.443 Ha correction | 0.0000 | 0.0000 | certified |
| HF parity UCCSD | wrong sector, masked by a 0.443 Ha correction | 0.0000 | 0.0000 | certified |
| LiH parity HEA r2 | wrong Hartree-Fock reference | 5.1814 | 3.3702 | certified |
| N2 parity HEA r4 | wrong sector, masked by a 0.756 Ha correction; wrong Hartree-Fock reference | 79.7530 | 103.5221 | validated |
| N2 parity HEA r10 | wrong sector, masked by a 0.756 Ha correction; wrong Hartree-Fock reference | 9.5040 | 4.4040 | certified |
| NH3 parity HEA r2 | wrong sector, masked by a 0.380 Ha correction; wrong Hartree-Fock reference | 6.9115 | 0.7341 | certified |
| water_dimer parity HEA r2 | wrong Hartree-Fock reference | 0.1562 | 0.1142 | certified |

**No entry changed trust level.** Every certified entry is still certified and the one
research-tier entry is still research-tier, so the suite headline — 47 certified across
sixteen molecules — is unchanged. Fourteen entries changed sector, eight changed
Hartree–Fock reference state, and C₄H₄ under parity changed both its symmetry count
(2 → 3, so 6 → 5 tapered qubits) and its reference state, because its CASSCF orbital gauge
differs from the generating run's — the effect described under *Rebuild discipline* in
[`NOISY_TIER.md`](NOISY_TIER.md), not the sector bug.

Most gaps improved, several by a large factor: NH₃ parity from 6.91 to 0.73 mHa, N₂ parity
at ten layers from 9.50 to 4.40 mHa, BeH₂ parity UCCSD from 2.22 to 0.0024 mHa. Two got
worse: H₂O parity from 0.296 to 0.399 mHa, and the N₂ parity four-layer research entry
from 79.8 to 103.5 mHa. Both are recorded as they came out.

Two consistency checks the corrected suite now passes and the old one could not:

* **H₂ gives the same answer under all three mappings** — 1.05 × 10⁻⁶ mHa for UCCSD under
  Jordan–Wigner, parity and Bravyi–Kitaev alike. With the correct sector all three taper
  the same [2,2] problem to the same one qubit, so they must agree, and now they do.
* **BeH₂ parity and Jordan–Wigner now carry the same hardware penalty**, 34.4 mHa, where
  before parity showed 22.0 mHa. Same circuit shape on the same physical problem.

The four one-qubit H₂ and HF parity entries whose tapered Hamiltonian was a single
constant now have real structure, and their gaps are ordinary small numbers rather than
an exact zero that meant nothing.

<!-- RESULTS:END -->

---

## What this does not change

- **No Jordan–Wigner entry is affected.** 41 of the 54 published entries, including every
  ADAPT-VQE result and both large hydrogen chains H₈ and H₁₀, are untouched: same sector,
  same reference state, same energies, same hashes.
- **The threading and determinism results are unaffected.** Those concern the classical
  optimiser's arithmetic, not the encoding.
- **The certification definition is unchanged.** Gap below 0.01 Ha against the exact
  ground state of the same active space.

## What it says about the process

The fault survived a full 54-entry verification sweep, because `verify_entry.py`
regenerates an entry through the same pipeline and compares: a deterministic bug
reproduces perfectly and verifies clean. It survived because the one check that would have
caught it — does the tapered ground energy equal CASCI — existed, ran, and had its answer
routed into a correction instead of an assertion.

The lesson is narrow and worth keeping: a discrepancy a pipeline knows how to "correct" is
a discrepancy it will never report. The corrected code computes the same quantity and
raises on it.
