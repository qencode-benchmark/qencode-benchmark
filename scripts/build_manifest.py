#!/usr/bin/env python3
from __future__ import annotations

"""
Build a reproducible manifest.json for a directory.

The manifest includes:
- per-file sha256 + size
- overall sha256 fingerprint of the set

Usage:
  python3 scripts/build_manifest.py --root releases/v2/trusted --out releases/v2/trusted/manifest.json
  python3 scripts/build_manifest.py --root releases/v2/db --out releases/v2/db/manifest.json
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


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

    entries: List[Dict[str, object]] = []
    rows: List[Tuple[str, str]] = []

    for p in files:
        rel = p.relative_to(root).as_posix()
        sha = _sha256_file(p)
        size = p.stat().st_size
        rows.append((rel, sha))
        entries.append({"path": rel, "bytes": size, "sha256": sha})

    manifest = {
        "manifest_version": "1.0.0",
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

