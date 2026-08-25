"""
Phase 13: Standard Benchmark Suite v1 — load, expand, validate the frozen official suite.

One canonical definition (benchmarks/standard/suite_v1.yaml) → deterministic list of
benchmark runs and cells (entry × backend) for run_standard_suite and validate_standard_suite.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Backend names in suite YAML vs run_benchmark
_BACKEND_ALIASES = {"ideal": "statevector", "shots": "shots", "noisy": "noisy", "mitigated": "mitigated"}


def _normalize_active_space(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, list):
        return ",".join(str(x) for x in val)
    return str(val).strip() or None


def _normalize_mapping(m: str) -> str:
    m = (m or "").strip().lower()
    if m in ("jw", "jordan-wigner"):
        return "jordan_wigner"
    if m in ("bk", "bravyi-kitaev"):
        return "bravyi_kitaev"
    if m == "parity":
        return "parity"
    return m or "jordan_wigner"


def _normalize_ansatz_type(a: str) -> str:
    a = (a or "").strip().lower()
    if a in ("he", "hardware-efficient"):
        return "hardware_efficient"
    if a == "uccsd":
        return "uccsd"
    return a or "uccsd"


def load_standard_suite(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load suite definition from YAML. Default path: benchmarks/standard/suite_v1.yaml (repo-relative).
    """
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required. pip install pyyaml")

    if path is None:
        # Default: repo root is parent of src/qencode
        _repo = Path(__file__).resolve().parents[1]
        path = _repo / "benchmarks" / "standard" / "suite_v1.yaml"
    path = Path(path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Suite not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    validate_standard_suite(raw)
    return raw


def validate_standard_suite(suite: Dict[str, Any]) -> None:
    """
    Validate suite structure (required keys). Raises ValueError if invalid.
    """
    required = ["name", "version", "molecules", "mappings", "ansatzes", "execution"]
    missing = [k for k in required if k not in suite]
    if missing:
        raise ValueError(f"Suite missing required keys: {missing}")
    exec_cfg = suite.get("execution") or {}
    if "backends" not in exec_cfg:
        raise ValueError("Suite execution.backends required")
    mols = suite.get("molecules") or []
    if not mols:
        raise ValueError("Suite must define at least one molecule")
    for i, m in enumerate(mols):
        if not m.get("name"):
            raise ValueError(f"Suite molecule[{i}] must have 'name'")
    if not suite.get("mappings"):
        raise ValueError("Suite mappings must be non-empty")
    if not suite.get("ansatzes"):
        raise ValueError("Suite ansatzes must be non-empty")


def expand_standard_suite(suite: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Expand suite to full list of run jobs and cells.

    - run_jobs: one per (molecule, mapping, ansatz). Each is run once with --backend all.
    - cells: one per (molecule, mapping, ansatz, backend) for reporting and validation.

    Returns (run_jobs, cells). run_jobs have keys suitable for run_benchmark (molecule, mapping,
    ansatz, basis, variant, active_space, ansatz_reps, backend_run, shots, optimizer, max_iter).
    """
    molecules = suite.get("molecules") or []
    mappings = suite.get("mappings") or []
    ansatzes = suite.get("ansatzes") or []
    execution = suite.get("execution") or {}
    backends = execution.get("backends") or ["ideal", "shots", "noisy"]
    shots = execution.get("shots") or 8192
    optimizer_cfg = suite.get("optimizer") or {}
    opt_type = (optimizer_cfg.get("type") or "cobyla").strip().upper()
    max_iter = int(optimizer_cfg.get("max_iter") or 200)

    run_jobs: List[Dict[str, Any]] = []
    cells: List[Dict[str, Any]] = []

    for mol in molecules:
        name = str(mol.get("name") or "").strip()
        variant = str(mol.get("variant") or "default").strip() or "default"
        basis = str(mol.get("basis") or "sto3g").strip()
        active_space = _normalize_active_space(mol.get("active_space"))
        # Per-molecule backend override (e.g. skip noisy for heavy molecules)
        mol_backends = mol.get("backends_override") or backends

        for map_name in mappings:
            mapping_norm = _normalize_mapping(str(map_name))
            mapping_display = map_name if isinstance(map_name, str) else str(map_name)

            for ans in ansatzes:
                atype = (ans.get("type") or "uccsd") if isinstance(ans, dict) else "uccsd"
                reps = int(ans.get("reps", 1)) if isinstance(ans, dict) else 1
                ansatz_norm = _normalize_ansatz_type(str(atype))

                # Compute canonical backend list for this molecule
                mol_backends_canonical = [
                    _BACKEND_ALIASES.get((be or "").strip().lower(), (be or "").strip().lower())
                    for be in mol_backends
                ]
                # Use "all" only when all three default backends are included
                _default_set = {"statevector", "shots", "noisy"}
                backend_run = (
                    "all"
                    if _default_set.issubset(set(mol_backends_canonical))
                    else ",".join(mol_backends_canonical)
                )

                job = {
                    "molecule": name,
                    "variant": variant,
                    "basis": basis,
                    "active_space": active_space,
                    "mapping": mapping_norm,
                    "mapping_display": mapping_display,
                    "ansatz_type": ansatz_norm,
                    "ansatz_reps": reps,
                    "backend_run": backend_run,
                    "backend_run_list": mol_backends_canonical,
                    "shots": shots,
                    "optimizer": opt_type,
                    "max_iter": max_iter,
                }
                run_jobs.append(job)

                for be in mol_backends:
                    backend_canonical = _BACKEND_ALIASES.get((be or "").strip().lower(), (be or "").strip().lower())
                    if backend_canonical not in ("statevector", "shots", "noisy", "mitigated"):
                        backend_canonical = "statevector" if be == "ideal" else str(be)
                    cells.append({
                        **job,
                        "backend": backend_canonical,
                        "backend_display": be,
                    })

    return (run_jobs, cells)


def get_suite_summary(suite: Dict[str, Any]) -> Dict[str, Any]:
    """Return summary counts from suite (without expanding)."""
    molecules = suite.get("molecules") or []
    mappings = suite.get("mappings") or []
    ansatzes = suite.get("ansatzes") or []
    execution = suite.get("execution") or {}
    backends = execution.get("backends") or ["ideal", "shots", "noisy"]
    n_runs = len(molecules) * len(mappings) * len(ansatzes)
    n_cells = n_runs * len(backends)
    return {
        "name": suite.get("name"),
        "version": suite.get("version"),
        "n_molecules": len(molecules),
        "n_mappings": len(mappings),
        "n_ansatzes": len(ansatzes),
        "n_backends": len(backends),
        "total_run_jobs": n_runs,
        "total_cells": n_cells,
    }


def _entry_signature(entry: Dict[str, Any]) -> Optional[Tuple[str, str, str, str, str, int]]:
    """Extract (molecule, variant, basis, mapping, ansatz_type, reps) from entry for matching."""
    problem = entry.get("problem") or {}
    enc = entry.get("encoding") or {}
    name = problem.get("name")
    variant = str(problem.get("variant") or "default").strip() or "default"
    basis = problem.get("basis")
    mapping = enc.get("mapping")
    atype = enc.get("ansatz_type")
    reps = enc.get("ansatz_reps")
    if not all([name, basis, mapping, atype]):
        return None
    try:
        r = int(reps) if reps is not None else 1
    except Exception:
        r = 1
    return (
        str(name).strip().lower(),
        variant.lower(),
        str(basis).strip().lower(),
        _normalize_mapping(str(mapping)),
        _normalize_ansatz_type(str(atype)),
        r,
    )


def find_entry_for_job(db_dir: Path, job: Dict[str, Any]) -> Optional[Path]:
    """Find entry path in db_dir that matches this run job (molecule, variant, basis, mapping, ansatz, reps)."""
    sig_want = (
        (job.get("molecule") or "").lower(),
        (job.get("variant") or "default").lower(),
        (job.get("basis") or "sto3g").lower(),
        _normalize_mapping(str(job.get("mapping") or "")),
        _normalize_ansatz_type(str(job.get("ansatz_type") or "")),
        int(job.get("ansatz_reps") or 1),
    )
    ignore = {
        "index.json", "benchmarks.csv", "manifest.json", "entry_content_hashes.json",
        "trusted_index.json", "trusted_benchmarks.csv", "canonical_index.json",
    }
    import json as _json
    for p in db_dir.glob("*.json"):
        if p.name in ignore or "__sha256_" not in p.name or "_v2__sha256_" not in p.name:
            continue
        try:
            d = _json.loads(p.read_text(encoding="utf-8"))
            sig = _entry_signature(d)
            if sig == sig_want:
                return p
        except Exception:
            continue
    return None


def get_required_metrics(suite: Dict[str, Any]) -> List[str]:
    """Return list of required metric keys from suite output.require_metrics (default: benchmark_core keys)."""
    out = suite.get("output") or {}
    req = out.get("require_metrics")
    if req:
        return list(req)
    return [
        "vqe_energy", "exact_energy", "gap_ideal", "gap_shots", "gap_noisy",
        "depth", "num_2q_gates", "terms", "groups",
    ]
