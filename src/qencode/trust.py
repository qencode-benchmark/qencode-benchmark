"""
Phase 15: Result trust levels — Experimental, Validated, Certified.

Determines trust level from entry content; used by assign_trust_levels, audit, dashboard, compare/rank.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

LEVEL_EXPERIMENTAL = "experimental"
LEVEL_VALIDATED = "validated"
LEVEL_CERTIFIED = "certified"

_REQUIRED_CORE_KEYS = [
    "molecule", "basis", "mapping", "ansatz",
    "vqe_energy", "exact_energy", "gap_ideal", "gap_shots", "gap_noisy", "gap_mit",
    "depth", "num_2q_gates", "terms", "groups",
]


def _extract_core(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal benchmark_core extraction for trust checks (no fill)."""
    problem = entry.get("problem") or {}
    enc = entry.get("encoding") or {}
    artifacts = entry.get("artifacts") or {}
    qh = artifacts.get("qubit_hamiltonian") or {}
    results = entry.get("results") or {}
    ref = results.get("reference") or {}
    vqe = results.get("vqe") or {}
    vqe_shots = results.get("vqe_shots") or {}
    vqe_noisy = results.get("vqe_noisy") or {}
    vqe_mit = results.get("vqe_mitigated") or {}
    quality = results.get("quality") or {}
    circuit_stats = entry.get("circuit_stats") or {}
    execution = entry.get("execution") or {}
    meas = execution.get("measurement") or {}

    vqe_energy = vqe.get("best_energy_hartree_like") or vqe.get("best_energy")
    exact_energy = ref.get("exact_qubit_ground_energy_hartree_like")
    gap_ideal = quality.get("abs_vqe_exact_gap")
    if gap_ideal is None and exact_energy is not None and vqe_energy is not None:
        gap_ideal = abs(float(vqe_energy) - float(exact_energy))

    def _gap(best: Any, ex: Any) -> Optional[float]:
        if best is None or ex is None:
            return None
        try:
            return abs(float(best) - float(ex))
        except (TypeError, ValueError):
            return None

    gap_shots = _gap(vqe_shots.get("best_energy"), exact_energy)
    gap_noisy = _gap(vqe_noisy.get("best_energy"), exact_energy)
    gap_mit = _gap(vqe_mit.get("best_energy"), exact_energy)

    depth = circuit_stats.get("ansatz_depth")
    if depth is None and isinstance(vqe.get("circuit_metrics"), dict):
        depth = vqe["circuit_metrics"].get("ansatz_depth")
    num_2q = circuit_stats.get("ansatz_num_2q_gates")
    if num_2q is None and isinstance(vqe.get("circuit_metrics"), dict):
        num_2q = vqe["circuit_metrics"].get("ansatz_num_2q_gates")

    terms = qh.get("num_pauli_terms")
    if terms is None and isinstance(qh.get("pauli_terms"), list):
        terms = len(qh["pauli_terms"])
    groups = meas.get("num_groups")

    return {
        "molecule": str(problem.get("name") or ""),
        "basis": str(problem.get("basis") or ""),
        "mapping": str(enc.get("mapping") or ""),
        "ansatz": str(enc.get("ansatz_type") or ""),
        "vqe_energy": vqe_energy,
        "exact_energy": exact_energy,
        "gap_ideal": gap_ideal,
        "gap_shots": gap_shots,
        "gap_noisy": gap_noisy,
        "gap_mit": gap_mit,
        "depth": depth,
        "num_2q_gates": num_2q,
        "terms": terms,
        "groups": groups,
    }


def validate_for_validated(entry: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validated: schema-consistent, benchmark_core complete, exact energy present, critical metrics non-null.
    Returns (ok, list of reasons / missing).
    """
    core = _extract_core(entry)
    missing_keys = [k for k in _REQUIRED_CORE_KEYS if k not in core]
    if missing_keys:
        return False, [f"benchmark_core missing keys: {missing_keys}"]

    if core.get("vqe_energy") is None:
        return False, ["vqe_energy missing"]
    if core.get("exact_energy") is None:
        return False, ["exact_energy missing"]

    # At least one gap for quality signal
    if (core.get("gap_ideal") is None and core.get("gap_noisy") is None and core.get("gap_shots") is None):
        return False, ["no gap_ideal/gap_shots/gap_noisy (incomplete run)"]

    return True, ["schema_consistent", "benchmark_core_complete", "exact_energy_present", "metrics_complete"]


def validate_for_certified(
    entry: Dict[str, Any],
    suite_spec: Optional[Dict[str, Any]] = None,
    gap_threshold: float = 0.01,
    require_manifest_verified: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Certified: validated + in standard suite (if suite_spec given) + trusted (gap ≤ threshold) + optional manifest.
    Returns (ok, list of reasons or failure reasons).
    """
    ok_val, reasons_val = validate_for_validated(entry)
    if not ok_val:
        return False, reasons_val

    reasons: List[str] = list(reasons_val)

    # Trusted subset: exact present, gap ≤ threshold, results.quality.trusted
    quality = (entry.get("results") or {}).get("quality") or {}
    if not quality.get("trusted"):
        return False, reasons_val + ["results.quality.trusted not true"]
    core = _extract_core(entry)
    try:
        gap = float(core.get("gap_ideal") or 0)
        if gap > gap_threshold:
            return False, reasons_val + [f"gap_ideal {gap} > threshold {gap_threshold}"]
    except (TypeError, ValueError):
        return False, reasons_val + ["gap_ideal invalid"]

    reasons.append("trusted_subset_pass")

    # In standard suite (if spec provided)
    if suite_spec is not None:
        from qencode.certification import is_entry_in_standard_suite
        if not is_entry_in_standard_suite(entry, suite_spec):
            sv = suite_spec.get("version") if isinstance(suite_spec, dict) else None
            sv_str = str(sv) if sv is not None else "unknown"
            return False, reasons_val + [f"not in standard suite v{sv_str} grid"]
        sv = suite_spec.get("version") if isinstance(suite_spec, dict) else None
        sv_str = str(sv) if sv is not None else "unknown"
        reasons.append(f"matches_standard_suite_v{sv_str}")

    # Manifest (optional)
    if require_manifest_verified:
        # Caller can set this when manifest exists and was verified
        # We don't verify here; assign_trust_levels/audit can set manifest_verified in reasons
        pass

    return True, reasons + ["certified"]


def determine_trust_level(
    entry: Dict[str, Any],
    suite_spec: Optional[Dict[str, Any]] = None,
    gap_threshold: float = 0.01,
) -> Tuple[str, List[str]]:
    """
    Determine trust level: certified > validated > experimental.
    Returns (level, reasons). Reasons explain why this level (e.g. ["schema_valid", "metrics_complete"]).
    """
    # Try certified first
    if suite_spec is not None:
        ok_cert, reasons_cert = validate_for_certified(entry, suite_spec=suite_spec, gap_threshold=gap_threshold)
        if ok_cert:
            return LEVEL_CERTIFIED, reasons_cert

    # Try validated
    ok_val, reasons_val = validate_for_validated(entry)
    if ok_val:
        return LEVEL_VALIDATED, reasons_val

    # Experimental: incomplete or failed validation
    return LEVEL_EXPERIMENTAL, ["incomplete_or_unvalidated"] + reasons_val
