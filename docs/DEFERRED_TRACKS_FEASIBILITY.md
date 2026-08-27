# Deferred tracks: what each would actually cost

Three expansion tracks have been deferred on the grounds that breadth dilutes the one
property that makes this benchmark distinctive. That is a judgement about cost, and it was
being made without measuring the cost. These probes measure it.

**Nothing here changes the suite.** No entries were written, no hashes touched. The scripts
are in `tools/probe_*.py` and can be re-run.

| track | verdict |
|---|---|
| Multi-backend | **Conditionally viable** — safe for gradient-based entries, unsafe for gradient-free ones |
| cc-pVTZ | **Cheaper than assumed** — the quantum side is nearly free; the cost is the re-baseline |
| Transition metals | **Would mostly produce research-tier entries** — one plausible candidate |
| DMRG / selected-CI | **Skip permanently** — no probe needed, see below |

## Decisions taken (2026-08-27)

These probes were run to inform four decisions, which are now settled. The first two are
written into [`LEADERBOARD_RULES_V2.md`](LEADERBOARD_RULES_V2.md) as dated amendments, so
they govern eligibility rather than living only in a document like this one.

1. **`default.qubit` stays the source of truth.** Any certified entry whose optimiser
   contains a gradient-free component — plain COBYLA, or ADAPT-VQE with a COBYLA inner
   optimiser — must be produced on it. That is 47 of the 54 current entries.
2. **`lightning.qubit` is an optional, clearly labelled path for fully gradient-based
   entries only**, carrying an explicit warning about trajectory divergence. 7 of 54
   entries would be eligible today.
3. **The suite is frozen** — no basis change, no new molecules, no transition metals —
   until the paper pending on the v4.4 numbers is published.
4. **DMRG and selected-CI are dropped**, not deferred.

Effort continues on the items these probes were competing with: surfacing the classical
baselines and resource estimates already in the database, packaging and a genuine
five-minute quickstart, and the consolidated write-up of the shot-noise recommendations in
[`SHOT_NOISE_AND_ALLOCATION.md`](SHOT_NOISE_AND_ALLOCATION.md).

---

## 1. Multi-backend

`lightning.qubit` is available alongside `default.qubit` and runs about **1.8× faster**.
The question is not speed but whether entries produced on different backends are
comparable at the digits certification depends on.

Worst disagreement between the two backends, across H₂O, LiH, N₂ and benzene:

| test | worst \|Δ\| | in mHa |
|---|---|---|
| single energy evaluation at a fixed point | 2.56 × 10⁻¹³ Ha | 0.0000 |
| after COBYLA (gradient-free) | 2.40 × 10⁻³ Ha | **2.40** |
| after L-BFGS-B (parameter-shift gradient) | 1.55 × 10⁻⁶ Ha | 0.0015 |

Each backend reproduces itself exactly. The two backends agree on the *arithmetic* to
10⁻¹³. They then diverge by **ten orders of magnitude more than that** once a gradient-free
optimiser is placed on top.

This is the threaded-BLAS mechanism again, in a new place. A 10⁻¹³ difference flips a
comparison between two nearly equal energies, COBYLA takes a different step, and on a
multi-modal landscape the run lands in a different local minimum. In a separate run at a
shorter iteration budget, benzene differed by **11.03 mHa** between backends — larger than
the 10 mHa certification threshold. The magnitude is not stable because it is a question of
which basin the run falls into.

**Verdict.** A backend axis is publishable for gradient-based and ADAPT entries, where the
disagreement stays at 10⁻⁶ Ha. It is *not* publishable for COBYLA entries without a stated
tolerance policy, because two backends can place the same configuration on opposite sides
of the certification line. Since much of the current suite is COBYLA, this is not the
free win a 1.8× speedup makes it look like.

---

## 2. cc-pVTZ

The assumption was that a larger basis means a larger, more expensive problem. On the
quantum side that turns out to be false.

| molecule | basis functions | qubits | Pauli terms | λ = Σ\|hₐ\| | E_CASCI shift |
|---|---|---|---|---|---|
| H₂ | 10 → 28 | 4 → 4 | 17 → 17 | — | −2.97 mHa |
| LiH | 19 → 44 | 8 → 8 | 229 → 229 | −1.8% | −2.97 mHa |
| H₂O | 24 → 58 | 8 → 8 | 125 → 125 | −0.8% | −30.09 mHa |
| N₂ | 28 → 60 | 12 → 12 | 489 → 489 | −0.6% | −19.78 mHa |

Qubit count is set by the active space, not the basis, so it does not move. The Pauli term
count is **identical** in every case. The Hamiltonian one-norm shifts by under 2%, so
T-gate estimates would move by about a percent rather than being rebuilt.

Classical preprocessing slows by 2–4×, which at these sizes means fractions of a second.

**Verdict.** A cc-pVTZ track costs almost nothing on the circuit side — same qubits, same
terms, same gate counts, T-gate estimates within ~1%. What it costs is **re-running and
re-hashing all 47 entries**, because the integrals and therefore the energies change. That
is a real cost but a narrower one than assumed: this is a *when*, not a *whether*.

The natural timing is after the paper currently pending on the v4.4 numbers is out, since
re-baselining moves every number the paper cites.

---

## 3. Transition metals

The concern was that transition-metal systems are strongly multireference and would land
in research tier, diluting the certified count. Measured, with two suite molecules as
controls:

| system | basis fns | HF converged | T1 diagnostic | CASCI leading weight |
|---|---|---|---|---|
| ScH | 48 | yes | **0.0100** | 0.9756 |
| CuH | 48 | yes | 0.0301 | 0.9980 |
| CrH | 48 | **NO** | 0.0431 | — |
| TiO | 57 | yes | **0.0447** | 0.9999 |
| N₂ *(control)* | 28 | yes | 0.0099 | 0.9469 |
| H₂O *(control)* | 24 | yes | 0.0053 | 0.9996 |

T1 above roughly 0.02 is the conventional signal that a single-reference description is
breaking down — and UCCSD and hardware-efficient ansätze are both built on a single
reference. Transition metals here have a **median T1 of 0.0366 against 0.0076 for the suite
controls**, nearly five times more multireference. CrH does not converge at Hartree-Fock at
all.

One diagnostic disagrees with the other, and that disagreement is informative. The CASCI
leading weights are all close to 1, which would normally mean an easy single-determinant
state. They look easy because the active spaces used here ([4,4] and [6,6]) are too small
to contain the d-shell correlation that T1 is detecting. **The honest reading is that these
systems need larger active spaces than the suite currently uses**, which is a different and
larger cost than simply adding a molecule.

**Verdict.** ScH is the one plausible candidate: T1 = 0.0100, below the danger threshold
and comparable to N₂, which is already certified. The rest would likely produce research-
tier entries and would need bigger active spaces to be worth doing at all.

---

## 4. DMRG / selected-CI — no probe needed

The suite's largest active space is [10,10]. CASCI solves that **exactly**, by
diagonalisation. DMRG and selected-CI exist to approximate a full-CI answer when the space
is too large to diagonalise, so on this suite they would approximate something already
computed exactly, at the cost of a new dependency.

They earn their place the moment an active space outgrows exact diagonalisation, roughly
past [16,16]. Until the suite goes there, this stays skipped — not deferred.

---

## Reproducing

```bash
python tools/probe_backend.py H2O LiH N2 benzene     # backend determinism and speed
python tools/probe_backend_mechanism.py              # is divergence arithmetic or optimiser?
python tools/probe_basis.py H2 LiH H2O N2            # what cc-pVTZ would cost
python tools/probe_transition_metals.py              # T1 and CASCI diagnostics
```

All are read-only with respect to the entry database.
