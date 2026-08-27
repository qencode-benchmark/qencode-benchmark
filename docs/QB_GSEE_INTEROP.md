# DARPA QB-GSEE interoperability

The [QB-GSEE benchmark](https://github.com/isi-usc-edu/qb-gsee-benchmark) is the DARPA
Quantum Benchmarking program's suite for ground-state energy estimation. It defines a
problem-instance format and a solution format, both with published JSON schemas.

QEncode produces almost exactly what a QB-GSEE solution asks for. `tools/qbgsee.py` makes
that explicit: it reports where the two benchmarks overlap, and renders a certified
QEncode entry as a QB-GSEE `solution.json`, validated against their schema rather than
against an assumption about it.

Nothing here modifies an entry or a hash.

---

## Where the two benchmarks meet

QB-GSEE carries 63 problem instances in four families: 20 small molecules, 23 transition
metals, 9 homogeneous catalysts and 11 planted solutions. QEncode carries 16 molecules.

**Five are the same chemical system**, and QB-GSEE's small-molecule instances use
**cc-pVDZ** among their basis sets — the same basis QEncode standardised on:

| QB-GSEE | QEncode | best QEncode entry | gap | QEncode bar | QB-GSEE bar |
|---|---|---|---|---|---|
| `h2_o_0` | H₂O | JW / UCCSD | 1.44 × 10⁻⁷ Ha | pass | **pass** |
| `h_f_0` | HF | PAR / UCCSD | 1.42 × 10⁻¹⁴ Ha | pass | **pass** |
| `li_h_0` | LiH | JW / UCCSD | 2.86 × 10⁻⁶ Ha | pass | **pass** |
| `n_h3_0` | NH₃ | JW / UCCSD | 3.25 × 10⁻⁵ Ha | pass | **pass** |
| `n2_0` | N₂ | JW / HEA, CASSCF | 4.51 × 10⁻³ Ha | pass | **FAIL** |

**QB-GSEE requires chemical accuracy — 0.00159362 Ha — which is 6.3× tighter than
QEncode's 10 mHa certification bar.** Four of the five overlapping molecules clear it
anyway; N₂ does not, at 4.5 mHa.

That N₂ is the one to miss is consistent with everything else measured about it: it is the
molecule that needs CASSCF orbitals, carries ten ansatz layers and 70 two-qubit gates, and
takes by far the largest gate-noise penalty.

### The caveat that limits this comparison

QB-GSEE instances ship their own FCIDUMP integrals and active spaces. A QEncode gap is
measured against *its own* active-space CASCI reference. So this compares **accuracy
achieved on comparable problems, not on byte-identical ones**. Running the actual QB-GSEE
FCIDUMPs is a separate job and needs their SFTP data access, which we do not have.

### What does not overlap

QEncode's hydrogen chains (H₄, H₆, H₈, H₁₀), conjugated systems (C₄H₄, C₄H₆, benzene),
water dimer, BeH₂ and H₂CO have no QB-GSEE counterpart. QB-GSEE's atoms, halogens,
transition metals, catalysts and planted solutions have none in QEncode.

One connection worth noting: QB-GSEE's transition-metal family includes **TiO**, which
[`DEFERRED_TRACKS_FEASIBILITY.md`](DEFERRED_TRACKS_FEASIBILITY.md) measured independently
at a T1 diagnostic of 0.0447 — nearly five times the suite average and firmly in the
regime where single-reference ansätze stop being reliable. If QEncode ever adds transition
metals, that family is where the two benchmarks would meet.

---

## Exporting an entry as a QB-GSEE solution

```bash
python tools/qbgsee.py compare

python tools/qbgsee.py export releases/v4/db/H2O_ccpvdz_JW_UCCSD_v4_tapered__sha256_*.json \
    --problem-instance problem_instance.h2_o_0.<uuid>.json \
    --name "..." --email "..." --institution "..." \
    --run-time-seconds <measured> \
    -o solution.json
```

All five overlapping molecules export and **validate against
`solution.schema.0.0.1.json`**.

### How the fields map

| QB-GSEE | QEncode source |
|---|---|
| `energy`, `energy_units` | `results.vqe.best_energy_hartree`, Hartree |
| `error_bound` | `results.quality.abs_vqe_exact_gap` |
| `quantum_resources.logical.num_T_gates_per_shot` | `circuit_stats.t_gate_estimate` |
| `quantum_resources.logical.num_logical_qubits` | FT estimate, else tapered register (flagged) |
| `solver_details` | pipeline identity and `provenance.tool_versions` |
| `solution_details` | entry id, **content hash**, ansatz, mapping, active space, leaderboard URL |

### Three places the tool refuses to guess

**Runtime.** QB-GSEE requires `run_time.overall_time.seconds`. QEncode entries record
`nfev` and **no wall-clock time at all**. Writing `0.0` would read as "instantaneous", so
the exporter refuses to run without an explicit `--run-time-seconds`, and says why. *This
is a real gap in what entries record and worth fixing in the pipeline.*

**Task selection.** An instance carries one task per basis set — the H₂O instance has
cc-pVDZ, cc-pVTZ and cc-pVQZ. Submitting a cc-pVDZ result against the cc-pVQZ task would
be a silent category error, so the exporter matches the entry's basis to the task and
prints which one it chose.

**The signature.** QEncode signs entries with Ed25519, but over *its own* payload, not over
the QB-GSEE object. Presenting it as a QB-GSEE `digital_signature` would misrepresent what
was signed, so that field is `null` and the verifiable entry content hash is carried in
`solution_details` instead.

### `is_resource_estimate` is set to true

QEncode energies come from exact statevector simulation and its quantum resources from a
qubitized-QPE model. Nothing was executed on hardware, and `num_shots` is set to 1 to match
the single-run resource estimate rather than implying a sampling campaign that never
happened. `solution_details.energy_source` states this in the file itself.

---

## What this does not do

- **No import direction.** Running actual QB-GSEE instances needs their FCIDUMP files over
  SFTP. That is a separate piece of work and requires data access we do not have.
- **No submission.** The tool writes a file; submitting it is a decision for a person.
- **Not a claim of comparability on identical problems**, for the active-space reason above.

## Reproducing

```bash
python tools/qbgsee.py compare            # overlap and accuracy
python tools/qbgsee.py export --help      # full options
```

Schemas are fetched from the QB-GSEE repository and cached under `~/.cache/qbgsee`. Every
file written records the schema URL it was built against.
