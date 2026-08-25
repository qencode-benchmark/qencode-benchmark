"""
Phase 11: Workflow runner — run a workflow end-to-end and produce a workflow-aware summary.

Thin wrapper over run_benchmark: loads workflow, invokes run_benchmark, locates the entry,
extracts results, and optionally writes a workflow result JSON.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_REPO = Path(__file__).resolve().parents[2]


def _norm_mapping(s: str) -> str:
    m = (s or "").strip().lower()
    if m in ("jw", "jordan-wigner"):
        return "jordan_wigner"
    if m in ("bk", "bravyi-kitaev"):
        return "bravyi_kitaev"
    if m == "parity":
        return "parity"
    return m or "jordan_wigner"


def _norm_ansatz(s: str) -> str:
    a = (s or "").strip().lower()
    if a in ("he", "hardware-efficient"):
        return "hardware_efficient"
    if a == "uccsd":
        return "uccsd"
    return a or "uccsd"


def _entry_signature(d: Dict[str, Any]) -> Optional[Tuple[str, str, str, str, str, int]]:
    problem = d.get("problem") or {}
    enc = d.get("encoding") or {}
    name = problem.get("name")
    basis = problem.get("basis")
    mapping = enc.get("mapping")
    atype = enc.get("ansatz_type")
    reps = enc.get("ansatz_reps")
    if not all([name, basis, mapping, atype]):
        return None
    variant = str(problem.get("variant") or "default").strip() or "default"
    try:
        r = int(reps) if reps is not None else 1
    except Exception:
        r = 1
    return (
        str(name).strip().lower(),
        variant.lower(),
        str(basis).strip().lower(),
        _norm_mapping(str(mapping)),
        _norm_ansatz(str(atype)),
        r,
    )


def _find_entry(
    db_dir: Path,
    molecule: str,
    variant: str,
    basis: str,
    mapping: str,
    ansatz: str,
    ansatz_reps: int = 1,
) -> Optional[Path]:
    sig_want = (
        molecule.lower(),
        variant.lower(),
        basis.lower(),
        _norm_mapping(mapping),
        _norm_ansatz(ansatz),
        int(ansatz_reps),
    )
    ignore = {
        "index.json", "benchmarks.csv", "manifest.json", "entry_content_hashes.json",
        "trusted_index.json", "trusted_benchmarks.csv", "canonical_index.json",
    }
    for p in db_dir.glob("*.json"):
        if p.name in ignore or "__sha256_" not in p.name or "_v2__sha256_" not in p.name:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            sig = _entry_signature(d)
            if sig == sig_want:
                return p
        except Exception:
            continue
    return None


def _extract_workflow_results(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Extract workflow summary fields from an entry (same logic as benchmark_core)."""
    problem = entry.get("problem") or {}
    enc = entry.get("encoding") or {}
    results = entry.get("results") or {}
    ref = results.get("reference") or {}
    vqe = results.get("vqe") or {}
    vqe_noisy = results.get("vqe_noisy") or {}
    vqe_mit = results.get("vqe_mitigated") or {}
    quality = results.get("quality") or {}
    circuit_stats = entry.get("circuit_stats") or {}

    vqe_energy = vqe.get("best_energy_hartree_like") or vqe.get("best_energy")
    exact_energy = ref.get("exact_qubit_ground_energy_hartree_like")
    gap_ideal = quality.get("abs_vqe_exact_gap")
    if gap_ideal is None and exact_energy is not None and vqe_energy is not None:
        gap_ideal = abs(float(vqe_energy) - float(exact_energy))

    def _gap(best: Any, ex: Any) -> Optional[float]:
        if best is None or ex is None:
            return None
        return abs(float(best) - float(ex))

    gap_noisy = _gap(vqe_noisy.get("best_energy"), exact_energy)
    gap_mit = _gap(vqe_mit.get("best_energy"), exact_energy)

    depth = circuit_stats.get("ansatz_depth")
    if depth is None and isinstance(vqe.get("circuit_metrics"), dict):
        depth = vqe["circuit_metrics"].get("ansatz_depth")
    num_2q = circuit_stats.get("ansatz_num_2q_gates")
    if num_2q is None and isinstance(vqe.get("circuit_metrics"), dict):
        num_2q = vqe["circuit_metrics"].get("ansatz_num_2q_gates")

    return {
        "vqe_energy": vqe_energy,
        "exact_energy": exact_energy,
        "gap_ideal": gap_ideal,
        "gap_noisy": gap_noisy,
        "gap_mit": gap_mit,
        "depth": depth,
        "num_2q_gates": num_2q,
        "molecule": str(problem.get("name") or ""),
        "basis": str(problem.get("basis") or ""),
        "mapping": str(enc.get("mapping") or ""),
        "ansatz": str(enc.get("ansatz_type") or ""),
    }


def run_workflow(
    workflow_name: str,
    molecule: str,
    *,
    variant: str = "default",
    basis: str = "sto3g",
    active_space: Optional[str] = None,
    out_dir: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force: bool = False,
    fill_benchmark_core: bool = True,
) -> Tuple[Optional[Path], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Load workflow, run run_benchmark (subprocess), find the resulting entry, extract results.

    Returns (entry_path, workflow_config, results_dict).
    If run_benchmark fails, returns (None, workflow_config, None).
    """
    from qencode.workflows.loader import load_workflow

    repo = (repo_root or _REPO).resolve()
    out_dir = (out_dir or repo / "releases" / "v2" / "db").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    workflows_dir = repo / "workflows"
    config = load_workflow(workflow_name, workflows_dir=workflows_dir)
    mapping = str(config.get("mapping") or "jordan_wigner")
    ansatz = str((config.get("ansatz") or {}).get("type") or "uccsd")
    ansatz_reps = int((config.get("ansatz") or {}).get("reps") or 1)

    py = sys.executable
    cmd = [
        py,
        str(repo / "scripts" / "run_benchmark.py"),
        "--workflow", workflow_name,
        "--molecule", molecule,
        "--variant", variant,
        "--basis", basis,
        "--out-dir", str(out_dir),
        "--repo-root", str(repo),
    ]
    if active_space:
        cmd += ["--active-space", active_space]
    if fill_benchmark_core:
        cmd.append("--fill-benchmark-core")

    ret = subprocess.run(cmd, cwd=str(repo))
    if ret.returncode != 0:
        return (None, config, None)

    entry_path = _find_entry(out_dir, molecule, variant, basis, mapping, ansatz, ansatz_reps)
    if entry_path is None:
        return (None, config, None)

    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    results = _extract_workflow_results(entry)
    return (entry_path, config, results)


def save_workflow_result(
    result_path: Path,
    workflow_name: str,
    molecule: str,
    workflow_config: Dict[str, Any],
    results: Dict[str, Any],
) -> None:
    """Write workflow result JSON (metadata + results) for Phase 11 summary storage."""
    result_path = result_path.resolve()
    result_path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "workflow_name": workflow_name,
        "molecule": molecule,
        "mapping": workflow_config.get("mapping"),
        "ansatz": dict(workflow_config.get("ansatz") or {}),
        "optimizer": dict(workflow_config.get("optimizer") or {}),
        "execution": dict(workflow_config.get("execution") or {}),
        "measurement": dict(workflow_config.get("measurement") or {}),
        "mitigation": dict(workflow_config.get("mitigation") or {}),
        "results": {
            "vqe_energy": results.get("vqe_energy"),
            "exact_energy": results.get("exact_energy"),
            "gap_ideal": results.get("gap_ideal"),
            "gap_noisy": results.get("gap_noisy"),
            "gap_mit": results.get("gap_mit"),
            "depth": results.get("depth"),
            "num_2q_gates": results.get("num_2q_gates"),
        },
    }
    result_path.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
