"""
Phase 10: Workflow loader — read and validate workflow YAMLs.

Workflows are molecule-agnostic: same recipe applies to H2, BeH2, LiH, or any future molecule.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

_REPO = Path(__file__).resolve().parents[2]
_WORKFLOWS_DIR = _REPO / "workflows"

_REQUIRED = [
    "name",
    "mapping",
    "ansatz.type",
    "optimizer.type",
    "execution.backend",
    "measurement.strategy",
    "mitigation.type",
]


def _get_path(config: Dict[str, Any], path: str) -> Any:
    """Get nested key; path is dot-separated."""
    cur: Any = config
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def validate_workflow(config: Dict[str, Any]) -> None:
    """
    Validate that the workflow has all required fields.
    Raises ValueError with a message listing what is missing.
    """
    missing: List[str] = []
    for path in _REQUIRED:
        val = _get_path(config, path)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(path)
    backend = _get_path(config, "execution.backend")
    if backend in ("shots", "noisy"):
        if _get_path(config, "execution.shots") is None:
            missing.append("execution.shots")
    if missing:
        raise ValueError(f"Workflow missing required fields: {', '.join(missing)}")


def _normalize(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with defaults for optional fields."""
    out: Dict[str, Any] = {
        "name": config.get("name", ""),
        "mapping": (config.get("mapping") or "").strip().lower().replace("-", "_"),
        "ansatz": dict(config.get("ansatz") or {}),
        "optimizer": dict(config.get("optimizer") or {}),
        "measurement": dict(config.get("measurement") or {}),
        "mitigation": dict(config.get("mitigation") or {}),
        "execution": dict(config.get("execution") or {}),
        "metadata": dict(config.get("metadata") or {}),
    }
    out["ansatz"].setdefault("type", "uccsd")
    out["ansatz"].setdefault("reps", 1)
    out["optimizer"].setdefault("type", "cobyla")
    out["optimizer"].setdefault("max_iter", 200)
    out["measurement"].setdefault("strategy", "grouped")
    out["mitigation"].setdefault("type", "none")
    out["execution"].setdefault("backend", "statevector")
    out["execution"].setdefault("shots", None)
    return out


def load_workflow(name: str, workflows_dir: Path | None = None) -> Dict[str, Any]:
    """
    Load workflow by name. Looks for workflows/<name>.yaml.
    Validates required fields and returns normalized config.
    Works for any molecule — molecule is specified at run time (e.g. --molecule H2).
    """
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required for workflows. pip install pyyaml")

    workflows_dir = workflows_dir or _WORKFLOWS_DIR
    path = workflows_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    validate_workflow(raw)
    return _normalize(raw)


def list_workflows(workflows_dir: Path | None = None) -> List[str]:
    """Return list of available workflow names."""
    workflows_dir = workflows_dir or _WORKFLOWS_DIR
    if not workflows_dir.is_dir():
        return []
    return [p.stem for p in workflows_dir.glob("*.yaml")]
