#!/usr/bin/env python3
from __future__ import annotations

"""
Stamp v2 entries with an environment fingerprint under provenance.environment.

Usage:
  python3 scripts/stamp_env_v2.py --db-dir releases/v2/db --write
  python3 scripts/stamp_env_v2.py --db-dir releases/v2/db --write --overwrite
"""
import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    from importlib.metadata import version as pkg_version
except Exception:  # pragma: no cover
    pkg_version = None  # type: ignore

Json = Dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_nested(d: Json, path: Sequence[str], default: Any = None) -> Any:
    cur: Any = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def _set_nested(d: Json, path: Sequence[str], value: Any) -> None:
    cur: Any = d
    for k in path[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[path[-1]] = value


def _safe_pkg_version(name: str) -> Optional[str]:
    if pkg_version is None:
        return None
    try:
        return pkg_version(name)
    except Exception:
        return None


def environment_fingerprint() -> Json:
    import hashlib

    dep_lines: List[str] = []
    source = "importlib.metadata.distributions"

    try:
        from importlib.metadata import distributions  # py3.8+

        for dist in distributions():
            name = (dist.metadata.get("Name") or "").strip()
            ver = (dist.version or "").strip()
            if name and ver:
                dep_lines.append(f"{name}=={ver}")
    except Exception:
        source = "unavailable"
        dep_lines = []

    dep_lines_sorted = sorted(set(dep_lines), key=lambda s: s.lower())
    joined = "\n".join(dep_lines_sorted).encode("utf-8")
    dep_sha256 = hashlib.sha256(joined).hexdigest()

    return {
        "generated_utc": _utc_now(),
        "python_version": sys.version.replace("\n", " "),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": {
            "numpy": _safe_pkg_version("numpy"),
            "scipy": _safe_pkg_version("scipy"),
            "qiskit": _safe_pkg_version("qiskit"),
            "qiskit-terra": _safe_pkg_version("qiskit-terra"),
            "jsonschema": _safe_pkg_version("jsonschema"),
        },
        "dependency_fingerprint": {
            "source": source,
            "count": len(dep_lines_sorted),
            "sha256": dep_sha256,
        },
    }


def iter_entry_files(db_dir: Path) -> List[Path]:
    ignore = {
        "index.json",
        "benchmarks.csv",
        "trusted_index.json",
        "trusted_benchmarks.csv",
    }
    return sorted([p for p in db_dir.rglob("*.json") if p.name not in ignore])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True)
    ap.add_argument("--write", action="store_true", help="Actually write changes (default is dry-run)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing provenance.environment")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")

    env = environment_fingerprint()

    total = 0
    changed = 0

    for p in iter_entry_files(db_dir):
        total += 1
        d: Json = json.loads(p.read_text(encoding="utf-8"))

        existing = _get_nested(d, ["provenance", "environment"])
        if existing is not None and not args.overwrite:
            continue

        _set_nested(d, ["provenance", "environment"], env)
        changed += 1

        if args.write:
            p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    mode = "WRITE" if args.write else "DRY-RUN"
    print(f"✅ stamp_env_v2: OK total={total} changed={changed} mode={mode}")


if __name__ == "__main__":
    main()

