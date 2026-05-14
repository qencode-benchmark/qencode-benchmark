# QEncode v4 — Implementation Plan

> **Status: Planned.** v3.2 must be fully shipped first.
> **Goal:** Make QEncode the undisputed standard for quantum chemistry benchmarking,
> trusted by hardware companies, algorithm developers, pharma, and government labs —
> and charge accordingly.

---

## Why v4 exists

v3.x proved the pipeline works. v4 makes it worth paying for at enterprise scale.

The quantum industry has one burning question right now:

> *"We have a quantum computer. Does it actually outperform classical on real chemistry?"*

Nobody has a trustworthy, independent answer. QEncode v4 is that answer.

---

## Who pays and why

| Customer | What they need | What they'll pay for |
|----------|---------------|---------------------|
| **Quantum hardware companies** (IBM, IonQ, Rigetti, Quantinuum) | Independent proof their QPU outperforms competitors on real chemistry | Hardware certification runs — certified result on actual QPU, not simulation |
| **Quantum algorithm/software companies** (Classiq, QC Ware, Q-CTRL) | Proof their compiler/algorithm beats UCCSD on benchmark molecules | Algorithm certification — new ansatz type, certified gap + circuit cost |
| **Pharma and materials companies** | "Is quantum ready for my molecule?" feasibility answer | Custom molecule benchmarking, private results, NDA option |
| **Universities and research labs** | Reproducible, citable benchmark results for publications | Publication-grade certified entries (cc-pVDZ basis, CASSCF orbitals) |
| **Government / DARPA / DOE** | Independent readiness assessment, QB-GSEE alignment | Contract benchmarking, classified-molecule support |
| **Investors and VCs** | Due diligence: does this quantum company's claims hold up? | Benchmark report as a service |

---

## Revenue model (v4)

| Tier | Description | Price signal |
|------|-------------|-------------|
| **Self-run** (free) | Reproduce any entry locally using open-source code | Free — drives trust |
| **Certified simulation** | Managed run on QEncode infrastructure, signed receipt | Current model — $X/entry |
| **Certified hardware** | Run on real QPU, certified receipt + comparison vs simulation | 10–50× simulation price |
| **Enterprise molecule** | Custom molecule, private leaderboard, NDA | Project-based, $5k–$50k |
| **Fault-tolerant report** | Resource estimation report: logical qubits, T-gates, timeline | $2k–$10k per report |
| **API subscription** | Programmatic access to all benchmark data | $X/month, tiered by volume |

---

## Phase A — Foundation upgrade (ship first, unlocks everything)

### A1. Upgrade PennyLane to 0.45+ and NumPy to 2.0

**Why it matters commercially:**
The 6 currently-validated BK entries (LiH, H₂O, NH₃ BK/UCCSD and Parity/UCCSD) will
certify once PL 0.45 fixes the complex-taper bug. That takes the certified entry count
from 30 to up to 36 — a stronger benchmark set and a cleaner story for customers.

**Technical steps:**
1. Test PL 0.45 on existing v3.1 H₂, HF entries — confirm same energies within 1e-8 Ha
2. Confirm BK complex-taper bug is fixed (run LiH BK/UCCSD, check gap < 0.01 Ha)
3. Update `requirements-v3.txt` → `requirements-v4.txt`:
   - pennylane >= 0.45.0
   - numpy >= 2.0
   - pyscf == 2.6.x (latest stable)
4. Run the BK-validated molecules through the new pipeline and certify them
5. Update `.github/workflows/ci.yml` to use new requirements
6. Add a compatibility note to docs: v3.x entries generated with PL 0.44 / NumPy 1.26

**Files to change:** `requirements-v4.txt`, `.github/workflows/ci.yml`, `scripts/generate_entry_v4.py` (new file, inherits from v3)

---

### A2. New entry generator: `generate_entry_v4.py`

**Why:** v4 adds new fields (CASSCF orbitals, fault-tolerant estimates, hardware backend
results). Keeping a separate v4 generator preserves v3 reproducibility — v3.1 entries must
remain reproducible with v3 requirements forever.

**Technical steps:**
1. Copy `generate_entry_v3.py` → `generate_entry_v4.py`
2. Bump schema version to `4.0.0`
3. New output directory: `releases/v4/db/`
4. Add new fields to entry JSON:
   - `problem.orbital_optimization`: "hf" | "casscf" (new in v4)
   - `results.fault_tolerant`: resource estimation block (Phase C)
   - `encoding.backend`: "default.qubit" | "lightning.gpu" | "hardware:<provider>" (Phase C)
5. New catalog: `molecules_v4.json` (extends v3, adds larger molecules)

---

## Phase B — Benchmark expansion (makes the benchmark worth paying for)

### B1. Upgrade basis set to cc-pVDZ

**Why it matters commercially:**
6-31G is a teaching basis. cc-pVDZ (correlation-consistent polarized valence double-zeta)
is the first publication-grade basis. University and pharma customers won't cite 6-31G results
in papers — they will cite cc-pVDZ. This unlocks the research and pharma market.

**Technical:** Only change the `--basis` argument. PySCF and PennyLane handle it automatically.

**New entries to generate:** All 7 v3 molecules × 3 mappings × 2 ansatze = 42 entries in cc-pVDZ.
Run in the same order as v3.1: H₂ → HF → LiH → BeH₂ → H₂O → NH₃ → N₂.

**Expected qubit counts (cc-pVDZ vs 6-31G):**

| Molecule | Active space | JW qubits | Tapered qubits |
|----------|-------------|-----------|---------------|
| H₂ | [2e,2o] | 4 | 1 (same) |
| HF | [2e,2o] | 4 | 1 (same) |
| LiH | [4e,4o] | 8 | 4 |
| BeH₂ | [4e,4o] | 8 | 3 |
| H₂O | [4e,4o] | 8 | 4-5 |
| NH₃ | [4e,4o] | 8 | 4-5 |
| N₂ | [6e,6o] | 12 | 8 |

Active space sizes don't change — only the quality of the orbitals does. More correlation energy,
physically more realistic. cc-pVDZ correlation energies are 2–5× larger than 6-31G.

---

### B2. CASSCF-optimized orbitals

**Why it matters commercially:**
Current pipeline uses HF (Hartree-Fock) canonical orbitals for the active space. These are
not the best choice — CASSCF finds orbitals that maximize correlation captured by the active space.
Publication-grade quantum chemistry always uses CASSCF orbitals. This is the difference between
a result a PhD student will cite and one they won't.

**Technical steps:**
1. Add `run_casscf_orbitals()` to `generate_entry_v4.py`:
   ```python
   from pyscf import mcscf
   mc = mcscf.CASSCF(mf, n_orb, (n_alpha, n_beta))
   mc.kernel()
   # Use mc.mo_coeff for the active space instead of mf canonical orbitals
   ```
2. Pass CASSCF-optimized MO coefficients to PennyLane `molecular_hamiltonian` via the
   `mo_coeff` parameter
3. Store `orbital_optimization: "casscf"` in the entry JSON
4. Run a comparison: HF orbitals vs CASSCF orbitals on H₂O — verify CASSCF gives smaller gap
5. Add `--orbital-opt` CLI flag: `hf` (default, v3-compatible) | `casscf`

**Expected impact:** CASSCF orbitals typically reduce the VQE gap by 30–70% vs HF orbitals
for molecules with significant correlation (H₂O, NH₃, N₂). More certified entries, tighter gaps.

---

### B3. Larger molecules — benzene and beyond

**Why it matters commercially:**
Benzene (C₆H₆) is the "hello world" of quantum chemistry. Every quantum hardware and software
company wants to claim they solved benzene. Being the certification standard for benzene puts
QEncode at the center of every marketing claim in the industry. This is the single highest-value
addition in v4.

**Molecule roadmap:**

| Molecule | Formula | Active space | Qubits (JW) | Tapered (est.) | Why it matters |
|----------|---------|-------------|------------|----------------|---------------|
| Butadiene | C₄H₆ | [4e,4o] | 8 | 3–4 | Step toward benzene, NISQ-feasible |
| Pyrrole | C₄H₄NH | [6e,5o] | 10 | 5–6 | Biologically relevant, aromatic |
| **Benzene** | C₆H₆ | [6e,6o] | 12 | 6–8 | The landmark quantum chemistry target |
| Formaldehyde | H₂CO | [4e,4o] | 8 | 3–4 | Carbonyl group, pharma relevance |

**Tier assignment:**
- These start as "Research+" — larger active spaces, UCCSD may not certify
- Goal: HEA certifies; UCCSD certifies with CASSCF orbitals
- Anything that certifies is promoted to Certified tier

**Technical steps:**
1. Add geometries to `molecules_v4.json` (optimized at cc-pVDZ level using PySCF)
2. Test butadiene first (smallest of the new set) — confirm pipeline handles 8+ qubit systems
3. Benchmark GPU backend requirement (benzene at [6e,6o] will be slow on CPU)
4. Generate entries: start with JW only, add BK/Parity once JW certifies

---

## Phase C — Commercial features (direct revenue drivers)

### C1. Fault-tolerant resource estimation reports

**Why it matters commercially:**
This is the #1 question from enterprise customers and investors:
*"How many logical qubits and T-gates would fault-tolerant quantum hardware need
to outperform classical CCSD(T) on this molecule? And when will that hardware exist?"*

Nobody is answering this systematically for real chemistry benchmarks. QEncode can.

**What goes in a fault-tolerant report:**

| Metric | Description |
|--------|-------------|
| Logical qubit count | Qubits needed for fault-tolerant algorithm (Trotterization or QPE) |
| T-gate count | Non-Clifford gates (dominant cost on fault-tolerant hardware) |
| T-factory overhead | Additional physical qubits for magic state distillation |
| Physical qubit estimate | Total physical qubits at realistic error rates (1e-3) |
| Clock cycles | Total gate depth × cycle time |
| Classical wall time equivalent | What classical CPU time this replaces |
| Quantum advantage crossover | Estimated molecule size/precision where quantum wins |

**Technical steps:**
1. Add `fault_tolerant_estimate()` to `generate_entry_v4.py`:
   - Use Hamiltonian simulation cost formulas (Babbush et al. 2019, Lee et al. 2021)
   - Input: number of Pauli terms, system size, target precision
   - Output: T-gate count, logical qubit count
2. Integrate `openfermion.resource_estimates` or `fqe` (Fermionic Quantum Emulator)
3. Store results in `results.fault_tolerant` block in entry JSON
4. Build a PDF report generator: `scripts/generate_ft_report.py`
   - Takes an entry JSON + company name → produces a branded PDF
   - Includes molecule diagram, energy levels, resource estimate charts
   - This is the premium deliverable for enterprise customers

**Revenue:** Fault-tolerant reports are the highest-value product. A pharma company or
national lab will pay $5k–$20k for a credible answer to "is quantum useful for my molecule
by 2030?" QEncode can provide that answer with published methodology.

---

### C2. GPU-accelerated simulation backend

**Why it matters commercially:**
Benzene at [6e,6o] has a 64×64 Hamiltonian after JW mapping. On CPU (`default.qubit`),
each VQE function evaluation takes seconds; 10 multistart × 500 iterations = hours.
`lightning.gpu` is 50–200× faster. This makes v4 molecules practical to run.

**Technical steps:**
1. Install PennyLane-Lightning: `pip install pennylane-lightning[gpu]`
2. Add `--backend` CLI flag: `default.qubit` (default) | `lightning.qubit` | `lightning.gpu`
3. In `run_vqe()`: `dev = qml.device(args.backend, wires=wires)`
4. Add backend to entry JSON: `encoding.backend`
5. Update CI to use `lightning.qubit` (CPU-accelerated, available without GPU)
6. Note: GPU results must match CPU within 1e-8 Ha — add cross-check to verify script

**Impact:** v4 molecules become feasible to certify. GPU runs are 10–100× cheaper in
compute time → lower cost per entry → higher margin.

---

### C3. Hardware certification tier

**Why it matters commercially:**
Simulation-certified entries prove the algorithm works mathematically.
Hardware-certified entries prove the algorithm works on a real quantum computer.
This is what quantum hardware companies will pay premium prices for.

**How it works:**
1. Customer submits their QPU (or we partner with IBM/IonQ/Quantinuum via cloud API)
2. We run the same VQE circuit on real hardware with shot noise
3. We report:
   - Shot-noisy VQE energy vs exact CASCI reference
   - Hardware-vs-simulation gap
   - Error mitigation applied (ZNE, PEC, etc.)
   - Raw bitstring distribution
4. We issue a "Hardware Certification Receipt" — signed, timestamped, includes QPU
   device ID and calibration snapshot
5. Goes on a separate "Hardware Leaderboard" — ranked by hardware VQE gap and
   noise resilience score

**Technical steps (v4.1 — separate sub-phase):**
1. Add `--shots` flag to generator (currently always None = exact)
2. Integrate IBM Quantum via `qiskit-pennylane` plugin or direct Qiskit circuit export
3. Add error mitigation: Zero-Noise Extrapolation (ZNE) via PennyLane's `qml.transforms.mitigate_with_zne`
4. New entry schema fields: `hardware.device_id`, `hardware.shots`, `hardware.error_mitigation`,
   `hardware.raw_energy_hartree`, `hardware.mitigated_energy_hartree`
5. New website page: `/hardware-leaderboard`

**Revenue:** Hardware certification is the highest price-point product. IonQ paid $X to 
benchmark on their machine. IBM paid $Y. Results go on the hardware leaderboard — free
marketing for the hardware company, revenue for QEncode.

---

### C4. ADAPT-VQE ansatz

**Why it matters commercially:**
UCCSD uses a fixed set of excitation operators. ADAPT-VQE selects operators adaptively —
it grows the circuit only as much as needed, molecule by molecule. Leading quantum software
companies (Classiq, QC Ware) build on adaptive methods. They need a certified benchmark
for their approach.

Adding ADAPT-VQE to QEncode means:
- Smaller circuits than UCCSD (fewer 2-qubit gates) → better hardware performance
- Companies using ADAPT need QEncode as their benchmark standard
- New "Circuit Efficiency" leaderboard category

**Technical steps:**
1. Implement `build_adapt_vqe_circuit()` in `generate_entry_v4.py`
   - Use PennyLane's `qml.AdaptiveOptimizer` (available in PL 0.38+)
   - Or implement from scratch: gradient screening → add top operator → optimize → repeat
2. Add `--ansatz-type adapt` CLI option
3. New entry fields: `encoding.adapt_iterations`, `encoding.operator_pool_size`,
   `encoding.selected_operators`
4. Compare ADAPT vs UCCSD circuit depth on benzene — expected: ADAPT uses 50–70% fewer gates
5. New leaderboard column: "Circuit Depth" — ADAPT entries expected to dominate

---

## Phase D — Research and academic value

### D1. Excited states benchmarking

**Why it matters commercially:**
Drug discovery needs excited state energies (photochemistry, fluorescence, reactivity).
Current VQE benchmarks only target ground states. Adding excited states opens pharma
and materials science customers who care about optical properties.

**Technical steps:**
1. Add `--state` flag: `ground` (default) | `first_excited` | `second_excited`
2. Use `qml.qchem.excitations()` with state-averaged CASCI reference
3. New entry field: `problem.target_state`
4. New leaderboard tab: "Excited States"

---

### D2. Multi-reference methods comparison

**Why it matters commercially:**
CASCI/CASSCF is the gold standard active-space reference. But for strongly correlated systems
(N₂ triple bond, benzene) CCSD(T) is not a reliable classical baseline. Adding DMRG
(Density Matrix Renormalization Group) as an alternative classical reference would make
QEncode entries more credible to quantum chemistry reviewers.

**Technical steps:**
1. Add optional DMRG reference via `block2` Python package
2. Store as `results.classical_comparison.dmrg_energy_hartree` (if available)
3. New quality metric: `beats_dmrg` — VQE gap < DMRG correlation energy

---

## Phase E — Platform and recurring revenue

### E1. API access — programmatic benchmark data

**Why it matters commercially:**
Research groups, analytics teams at quantum companies, and algorithm developers want to
query benchmark data programmatically. Monthly subscription = recurring revenue.

**Technical steps:**
1. Add REST API routes to Next.js: `/api/v1/entries`, `/api/v1/leaderboard`, `/api/v1/molecules`
2. JWT authentication + API keys (tie to Lemon Squeezy subscription)
3. Rate limiting per tier (free: 100 calls/day, pro: unlimited)
4. OpenAPI spec + auto-generated docs at `/api/docs`

---

### E2. Enterprise private leaderboard

**Why it matters commercially:**
Quantum companies developing proprietary algorithms do not want their results public
before publication. An enterprise tier with private results, NDA, and then optional
public disclosure is how you charge $10k+ per engagement.

**Technical steps:**
1. Add `private` flag to entry schema
2. Private entries visible only to the customer in their dashboard
3. Optional "publish" button: moves to public leaderboard on their timeline
4. Website: private dashboard at `/dashboard/private`

---

## Implementation order and timeline

```
v4.0 — Foundation (ship first)
  ├── A1: PL 0.45 + NumPy 2.0 upgrade
  ├── A2: generate_entry_v4.py
  └── B1: cc-pVDZ basis set (same 7 molecules, better basis)

v4.1 — Benchmark expansion
  ├── B2: CASSCF-optimized orbitals
  ├── B3: Butadiene + Formaldehyde (new molecules)
  └── C2: GPU backend (required for larger molecules)

v4.2 — Benzene milestone (marketing event)
  ├── B3: Benzene [6e,6o] entries
  └── Launch: "QEncode certifies benzene" — press release, leaderboard update

v4.3 — Commercial features
  ├── C1: Fault-tolerant resource estimation + PDF reports
  ├── C4: ADAPT-VQE ansatz
  └── E1: API access + subscriptions

v4.4 — Hardware certification (biggest revenue unlock)
  ├── C3: Hardware backend integration (IBM/IonQ/Quantinuum)
  ├── Hardware leaderboard on website
  └── First hardware certification partnership

v4.5 — Research tier
  ├── D1: Excited states
  ├── D2: DMRG reference
  └── E2: Enterprise private leaderboard
```

---

## What stays the same from v3

- SHA-256 provenance hash (same algorithm, same `_strip_volatile()`)
- COBYLA VQE with multistart (remains the default optimizer)
- CASCI active-space FCI as the VQE reference energy
- Z2 symmetry tapering
- Certification criterion: `|E_VQE − E_CASCI| < |E_CCSD(T) − E_HF|`
- Ed25519 signing
- Open-source self-run reproducibility

v3.1 and v3.2 entries are never removed or modified. They remain on the leaderboard
and are reproducible with `requirements-v3.txt` forever.

---

## Definition of done for v4.0

- [ ] PL 0.45 confirmed working, BK complex-taper bug resolved
- [ ] `requirements-v4.txt` committed with pinned versions
- [ ] `generate_entry_v4.py` passes existing H₂ + HF entries within 1e-8 Ha of v3.1 values
- [ ] `schema_v4.json` with new fields documented
- [ ] All 42 cc-pVDZ entries generated, certified where expected, committed to `releases/v4/db/`
- [ ] `releases/v4/RELEASE_NOTES.md` written
- [ ] CI workflow updated to use v4 requirements
- [ ] GitHub Release `v4.0.0` tagged
- [ ] Website leaderboard shows v4 entries
