"""
Phase 8: Hardware profiles — simulate different quantum hardware conditions.

Load YAML profiles (nisq_small, nisq_medium, fault_tolerant) and convert to
run_vqe_v2 arguments (--noise, --p1, --p2, --shots).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO = Path(__file__).resolve().parents[2]
_PROFILES_DIR = _REPO / "profiles"


def load_profile(name: str, profiles_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load hardware profile by name. Looks for profiles/<name>.yaml.
    Returns dict with: name, qubits, one_qubit_error, two_qubit_error,
    readout_error, coherence_time_us, shots.
    """
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required for hardware profiles. pip install pyyaml")

    profiles_dir = profiles_dir or _PROFILES_DIR
    path = profiles_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        "name": raw.get("name", name),
        "qubits": int(raw.get("qubits", 20)),
        "one_qubit_error": float(raw.get("one_qubit_error", 0.001)),
        "two_qubit_error": float(raw.get("two_qubit_error", 0.01)),
        "readout_error": float(raw.get("readout_error", 0.02)),
        "coherence_time_us": float(raw.get("coherence_time_us", 100)),
        "shots": raw.get("shots"),
    }


def profile_to_vqe_args(profile: Dict[str, Any]) -> List[str]:
    """
    Convert profile to run_vqe_v2 CLI args.
    Returns e.g. ["--noise", "depolarizing", "--p1", "0.001", "--p2", "0.01", "--shots", "8192"].
    For fault_tolerant (zero errors), returns [] (ideal statevector).
    """
    p1 = profile.get("one_qubit_error", 0.001)
    p2 = profile.get("two_qubit_error", 0.01)
    shots = profile.get("shots")

    if p1 <= 0 and p2 <= 0:
        return []  # ideal

    args: List[str] = ["--noise", "depolarizing", "--p1", str(p1), "--p2", str(p2)]
    if shots is not None:
        args += ["--shots", str(int(shots))]
    return args


def list_profiles(profiles_dir: Optional[Path] = None) -> List[str]:
    """Return list of available profile names (from .yaml files)."""
    profiles_dir = profiles_dir or _PROFILES_DIR
    if not profiles_dir.is_dir():
        return []
    return [p.stem for p in profiles_dir.glob("*.yaml")]
