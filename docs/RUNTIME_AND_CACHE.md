# Runtime and Caching (Phase 14)

**Goal:** Make benchmark usage feel fast by reusing existing work and supporting resume and parallelism.

---

## What is implemented

### Layer 1 — Final result cache

- **Before running:** If the exact benchmark config (molecule, variant, basis, active_space, mapping, ansatz, reps, backend, optimizer, shots, grouping, mitigation, profile, workflow, out_dir) already has a cached result, return that entry path and skip the run.
- **After a successful run:** Store `config_hash -> entry_path` in the cache index.
- **Location:** `releases/v2/cache/results_index.json` (and `releases/v2/cache/` is in `.gitignore`).
- **Usage:** `run_benchmark.py --skip-if-cached` checks the cache before running; if hit, prints "Cache hit: ..." and exits 0. When run without `--skip-if-cached`, a successful run is stored automatically.

### Layer 2 — Intermediate artifact cache (stub)

- **API:** `cache.lookup_intermediate_artifact(key)`, `cache.store_intermediate_artifact(key, value)`.
- **Status:** Stubs only; to be implemented in Phase 14b (Hamiltonian, exact energy, grouped measurement sets, circuit metadata) when the pipeline is refactored to use them.

### Job registry

- **Purpose:** Track suite run status so you can resume after an interrupt.
- **Location:** `artifacts/standard_suite_v1_jobs.sqlite` (or `--registry <path>`).
- **Statuses:** `pending`, `running`, `completed`, `failed`, `skipped_cached`.
- **Usage:** `run_standard_suite.py` ensures all suite jobs are in the registry; with `--resume` (default) it only runs jobs that are still `pending`. After each job it updates the registry.

### Resume

- **Default:** `--resume` is on. Re-run `run_standard_suite.py` after a crash or Ctrl+C; it will skip completed and cached jobs and run only pending ones.
- **Re-run everything:** `run_standard_suite.py --no-resume` runs all jobs again (cache hits will still skip the actual VQE when looked up).

### Parallel workers

- **Usage:** `python scripts/run_standard_suite.py --workers 4`
- **Behavior:** Expands the suite to run jobs, filters to pending (if `--resume`), then runs them in a process pool of size N. The main process updates the job registry; workers only run `run_benchmark` and return success/failure and entry path.

### Runtime profiling

- **Script:** `scripts/profile_runtime.py`
- **Usage:** `python scripts/profile_runtime.py` (or `--jobs "H2:JW:uccsd:statevector,BeH2:BK:uccsd:noisy"`)
- **Output:** `artifacts/runtime_profile_suite_v1.csv` and `artifacts/runtime_profile_summary.md` with wall time per job. Use this to see where time is spent; for per-stage timing (Hamiltonian, exact solve, VQE, etc.) add instrumentation in Phase 14b.

---

## Quick reference

| Task | Command |
|------|--------|
| Run benchmark, skip if cached | `python scripts/run_benchmark.py --molecule H2 --mapping JW --ansatz uccsd --backend all --skip-if-cached` |
| Run suite with resume | `python scripts/run_standard_suite.py` (default: resume) |
| Run suite with 4 workers | `python scripts/run_standard_suite.py --workers 4` |
| Re-run all suite jobs | `python scripts/run_standard_suite.py --no-resume` |
| Profile runtime | `python scripts/profile_runtime.py` |

---

## Success criteria (Phase 14)

- Rerunning the same benchmark does not recompute when a cache entry exists (Layer 1).
- Interrupted suite generation can resume (registry + `--resume`).
- Runtime bottlenecks are measured via `profile_runtime.py`.
- Standard suite can run with `--workers N`.
- Cache hits are visible ("Cache hit: ..." and `skipped_cached` in the registry).

---

## Phase 14b (later)

- **Layer 2:** Implement intermediate artifact cache; refactor `generate_entry_v2` / `run_vqe_v2` to check and store Hamiltonian, exact energy, grouped measurement sets, circuit metadata.
- **Finer profiling:** Per-stage timings (Hamiltonian build, exact solve, ansatz construction, VQE optimization, noisy evaluation, metrics) inside the pipeline.
