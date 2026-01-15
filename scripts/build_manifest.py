#!/usr/bin/env python3
from __future__ import annotations

"""
Build a reproducible manifest.json for a directory.

The manifest includes:
- per-file sha256 + size
- overall sha256 fingerprint of the set
- for JSON entry files: extra metadata (entry_id, trusted, flags, energies)

Usage:
  python3 scripts/build_manifest.py --root releases/v2/trusted --out releases/v2/trusted/manifest.json
  python3 scripts/build_manifest.py --root releases/v2/db --out releases/v2/db/manifest.json
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

Json = Dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_files(root: Path) -> List[Path]:
    files = [p for p in root.rglob("*") if p.is_file()]
    # Ignore manifests themselves for stability
    files = [p for p in files if p.name not in {"manifest.json"}]
    return sorted(files, key=lambda p: p.as_posix().lower())


def _overall_fingerprint(rows: List[Tuple[str, str]]) -> str:
    """
    rows: list of (relative_path, sha256)
    """
    h = hashlib.sha256()
    for rel, sha in sorted(rows, key=lambda t: t[0].lower()):
        h.update(f"{rel} {sha}\n".encode("utf-8"))
    return h.hexdigest()


def _get_nested(d: Json, path: List[str]) -> Any:
    cur: Any = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def _as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    return None


def _is_entry_json(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    if path.name in {"index.json", "trusted_index.json"}:
        return False
    return True


def _extract_v2_summary(d: Json) -> Json:
    """
    Best-effort extraction for v2 entries.
    All fields are optional and will be None if missing.
    """
    entry_id = d.get("entry_id") or d.get("id") or None
    schema_version = d.get("schema_version") or d.get("version") or None

    # v2 preferred layout
    trusted = _get_nested(d, ["results", "quality", "trusted"])
    flags = _get_nested(d, ["results", "quality", "flags"])
    if flags is None:
        flags = _get_nested(d, ["results", "quality", "reasons"])

    hf = _as_float(_get_nested(d, ["results", "reference", "hf_energy_hartree"]))
    vqe = _as_float(_get_nested(d, ["results", "vqe", "best_energy_hartree"]))
    exact = _as_float(_get_nested(d, ["results", "reference", "exact_energy_hartree"]))

    # abs gap: prefer stored, else compute if possible
    abs_gap = _as_float(_get_nested(d, ["results", "quality", "abs_gap"]))
    if abs_gap is None and vqe is not None and exact is not None:
        abs_gap = abs(vqe - exact)

    return {
        "entry_id": entry_id,
        "schema_version": schema_version,
        "trusted": bool(trusted) if trusted is not None else None,
        "flags": flags if isinstance(flags, list) else None,
        "hf_energy_hartree": hf,
        "vqe_best_energy_hartree": vqe,
        "exact_energy_hartree": exact,
        "abs_gap": abs_gap,
    }


def _extract_v1_fallback_summary(d: Json) -> Json:
    """
    Fallback extraction for v1-like shapes (best effort).
    """
    entry_id = d.get("entry_id") or d.get("id") or None
    schema_version = d.get("schema_version") or d.get("version") or None

    hf = _as_float(_get_nested(d, ["validation", "classical_reference", "hf_energy_hartree_like"]))
    vqe = _as_float(_get_nested(d, ["validation", "vqe", "best_energy"]))
    exact = _as_float(_get_nested(d, ["validation", "exact_qubit_ground_energy", "energy"]))

    abs_gap = None
    if vqe is not None and exact is not None:
        abs_gap = abs(vqe - exact)

    return {
        "entry_id": entry_id,
        "schema_version": schema_version,
        "trusted": None,
        "flags": None,
        "hf_energy_hartree": hf,
        "vqe_best_energy_hartree": vqe,
        "exact_energy_hartree": exact,
        "abs_gap": abs_gap,
    }


def _extract_entry_summary(d: Json) -> Json:
    # Prefer v2 if it looks like v2
    if isinstance(_get_nested(d, ["results"]), dict):
        return _extract_v2_summary(d)
    return _extract_v1_fallback_summary(d)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Directory to fingerprint")
    ap.add_argument("--out", required=True, help="Output manifest.json path")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()

    if not root.exists() or not root.is_dir():
        raise SystemExit(f"--root must be an existing directory: {root}")

    files = _iter_files(root)

    entries: List[Json] = []
    rows: List[Tuple[str, str]] = []

    for p in files:
        rel = p.relative_to(root).as_posix()
        sha = _sha256_file(p)
        size = p.stat().st_size
        rows.append((rel, sha))

        rec: Json = {"path": rel, "bytes": size, "sha256": sha}

        if _is_entry_json(p):
            try:
                d: Json = json.loads(p.read_text(encoding="utf-8"))
                rec["entry"] = _extract_entry_summary(d)
            except Exception:
                rec["entry"] = {"parse_error": True}

        entries.append(rec)

    manifest = {
        "manifest_version": "1.1.0",
        "generated_utc": _utc_now(),
        "root_dir": root.as_posix(),
        "entry_count": len(entries),
        "files": entries,
        "overall_sha256": _overall_fingerprint(rows),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✅ manifest: wrote {out} files={len(entries)} overall_sha256={manifest['overall_sha256']}")


if __name__ == "__main__":
    main()

