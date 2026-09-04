# Trust Policy

What "certified" means on QEncode, what it does not mean, and what every other badge on
the leaderboard is. This document is the single definition. Where another document,
page or tool disagrees with it, this one is right and the other is a bug.

Applies to Suite v4 (cc-pVDZ). The definition has been the same in every suite the code has
ever produced — see [History](#history) for why an earlier version of this document said
otherwise.

---

## The certification criterion

An entry is **certified** when

```
|E_VQE − E_CASCI| < 0.01 Ha        (10 mHa)
```

where `E_CASCI` is the exact ground state of the qubit Hamiltonian in the entry's declared
active space, computed by CASCI on the same orbitals the VQE used. Nothing else enters the
criterion: not circuit cost, not the classical comparison, not who ran it.

This is the number every executable path applies —
`src/qencode/pipeline/generate_entry_v4.py` when it writes `results.quality.trusted`,
`scripts/export_leaderboard_v4.py` when it splits the leaderboard into tiers,
`scripts/verify_entry.py --mode certification` when it re-checks an entry, and
`tools/certification_margin.py` when it measures how much room an entry has. A test,
`tests/test_certification_definition.py`, checks that they all still agree and that this
document still says what they do.

**Why 10 mHa and not chemical accuracy.** Chemical accuracy is 1 kcal/mol ≈ 1.6 mHa. The
certification bar is deliberately looser, because the benchmark's purpose is to compare
*algorithms* — ansatz, optimiser, encoding — on a fixed problem, and a bar at 1.6 mHa would
leave the medium-sized systems (N₂, benzene, H₈, H₁₀) with no certified entries at all and
nothing to compare. Chemical accuracy is reported separately (below) so that the stricter
question is still answerable per entry.

---

## Tiers

| Tier | Condition | On the leaderboard |
|---|---|---|
| **Certified** | gap < 0.01 Ha | Accuracy, Lowest Cost and Balanced categories |
| **Research** | gap ≥ 0.01 Ha | Research category |

A research-tier entry is a correct, reproducible result that did not reach the bar —
usually because the method met its limit on a strongly correlated system. It is recorded,
published, hashed and signed exactly like a certified one. **Nothing is discarded**, and
an entry never moves between tiers after publication: the suite's molecule catalogue,
basis and active spaces are frozen, so a published gap is a fixed number.

---

## What certification attests

A certified entry carries four guarantees, each of them checkable:

1. **The procedure is fully declared.** Molecule, geometry, basis, active space, orbital
   treatment (HF or CASSCF), encoding, tapering sector, ansatz, optimiser, iteration
   budget, seed, and the exact package versions are all in the entry JSON.
2. **The result reproduces on the reference environment.** Re-running the declared
   procedure in the pinned environment (`requirements-v4.txt`, single-threaded BLAS)
   returns the stored energy to 10⁻⁶ Ha. Every one of the 54 published entries has been
   re-run this way — see [`VERIFICATION_SWEEP.md`](VERIFICATION_SWEEP.md).
3. **The entry has not been altered.** `entry_hash_sha256` covers the canonical JSON with
   volatile fields stripped, and the hash is Ed25519-signed by the project key.
4. **The gap is below 0.01 Ha** on that reproduced result.

## What certification does not attest

- **Not a hardware result.** Every entry is an exact statevector simulation. The
  same circuit on a device returns a different, noise-biased energy; measured
  penalties on this suite start at 34 mHa, above the bar — see
  [`GATE_NOISE.md`](GATE_NOISE.md).
- **Not bit-identical energies across machines.** For gradient-free optimisers the
  energy can move by up to ~10⁻² Ha on a different machine while still certifying,
  because a last-bit arithmetic difference can steer the optimiser into a different local
  minimum. Certification across machines is on *outcome* (the gap stays below the bar);
  bit-identity is guaranteed only on the reference environment. Two entries are known to
  fail re-certification on a drifted environment and are flagged, not withdrawn. The full
  statement is the dated amendments in
  [`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md).
- **Not chemical accuracy.** See the marker below.
- **Not "quantum beats classical".** See the badge below.

---

## Markers that are reported but are not certification

These appear alongside entries. None of them changes an entry's tier.

**Chemical accuracy** — gap < 1.6 mHa (1 kcal/mol). Shown on the leaderboard as the
inner threshold line. 26 of the 54 v4 entries reach it.

**Beats CCSD(T)** — `results.quality.beats_classical`, true when

```
|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|
```

i.e. the VQE error is smaller than the CCSD(T) correlation energy for the same molecule
and basis. This is a precision comparison within one molecular system against the best
single-reference perturbative classical method. It is an informational badge, independent
of the tier by definition. **It is not, and has never been in the code, the certification
criterion** — see [History](#history).

In Suite v4 it currently discriminates nothing: **all 54 entries carry it, including the
7 research-tier entries**, because cc-pVDZ CCSD(T) correlation energies are large enough
that even a 27 mHa gap clears them. That is precisely why it cannot be the criterion —
seven entries beat CCSD(T) and are not certified — and it is stated here so that the badge
is read as the weak, per-molecule comparison it is rather than as a mark of quality.

**Certification margin** — `0.01 Ha − gap`. How far an entry can move before it stops
certifying. Entries within 20% of the bar are flagged *thin-margin*; those that are also
on an amplifying (gradient-free optimiser, unstructured ansatz) configuration are flagged
*at-risk*; those that have been re-run on another environment carry the measured result
(*robust*, *marginal* or *fragile*). Tool: `tools/certification_margin.py`.

---

## Self-run and managed certification

The criterion is identical whoever runs the pipeline. Anyone can generate an entry with
the open pipeline, and `scripts/verify_entry.py` will check any published entry from a
clean checkout.

Managed certification (the paid service on the website) runs the same pipeline on the
project's reference environment and returns a signed receipt, the entry, and a
verification page. It adds an independent execution and a signature; it does not apply a
different bar, and it cannot make an entry certify that would not certify when self-run.

---

## Provenance fields

Every entry, either tier, carries:

- `entry_hash_sha256` — SHA-256 of the canonical entry with volatile fields removed
- `signature` — Ed25519 signature of that hash by the QEncode project key
- `provenance.tool_versions` — exact Python, PySCF, PennyLane, SciPy, NumPy versions
- `provenance.git_commit` — the pipeline revision that produced it
- `run_config` — optimiser, iteration budget, seed, restarts, backend
- `created_utc`

---

## History

**Suite v3.1 documents stated the criterion as `|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|`.**
That was never what the code applied. `scripts/generate_entry_v3.py` set `trusted` from
`abs_gap < 0.01` and `scripts/export_leaderboard_v3.py` split tiers at `GAP_THRESHOLD =
0.01`, the same as v4. The two conditions happened to agree on every v3.1 entry — all 30
certified entries also beat CCSD(T), and the 12 research entries (N₂, 6-31G) failed both —
so the discrepancy produced no wrong tier assignment. It was a documentation error, not a
result error, and it is corrected here rather than by editing the v3.1 release notes,
which are left as written with a pointer to this section.

The Beats CCSD(T) comparison is retained as the informational badge described above.

*Corrected 2026-09-04.*

---

## Related

- [`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md) — how certified entries are ranked,
  and the dated amendments on reproducibility, backends and margin
- [`VERIFICATION_SWEEP.md`](VERIFICATION_SWEEP.md) — the re-run of all 54 entries
- [`SUBMISSIONS.md`](SUBMISSIONS.md) — submitting an entry
- [`../SCHEMA.md`](../SCHEMA.md) — every field in an entry
