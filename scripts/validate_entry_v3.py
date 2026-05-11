#!/usr/bin/env python3
"""
Validate one or more v3 entries against schema_v3.json.

Usage:
  python scripts/validate_entry_v3.py releases/v3/db/H2_sto3g_JW_UCCSD_v3_tapered__sha256_*.json
  python scripts/validate_entry_v3.py releases/v3/db/          # validates all *.json files
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO   = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schema" / "schema_v3.json"

GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; RESET = "\033[0m"; BOLD = "\033[1m"

def _ok(m):   return f"{GREEN}  [OK]{RESET}  {m}"
def _warn(m): return f"{YELLOW}  [WARN]{RESET} {m}"
def _fail(m): return f"{RED}  [FAIL]{RESET} {m}"


def validate_file(path: Path) -> bool:
    try:
        import jsonschema
    except ImportError:
        print(_warn("jsonschema not installed -- install with: pip install jsonschema"))
        print(_warn("Falling back to manual checks only"))
        return manual_check(path)

    schema = json.loads(SCHEMA.read_text())
    entry  = json.loads(path.read_text())

    try:
        jsonschema.validate(entry, schema)
    except jsonschema.ValidationError as e:
        print(_fail(f"{path.name}: {e.message}  (path: {list(e.path)})"))
        return False

    # Extra sanity checks beyond JSON schema
    ok = True
    q = entry.get("results", {}).get("quality", {})
    sv = entry.get("schema_version", "")

    if not sv.startswith("3."):
        print(_fail(f"{path.name}: schema_version must start with '3.' (got '{sv}')"))
        ok = False

    gap = q.get("abs_vqe_exact_gap")
    trusted = q.get("trusted", False)
    if gap is not None:
        if trusted and gap >= 0.01:
            print(_warn(f"{path.name}: trusted=True but gap={gap:.4e} >= 0.01 Ha -- inconsistent"))
        if not trusted and gap < 0.01:
            print(_warn(f"{path.name}: trusted=False but gap={gap:.4e} < 0.01 Ha -- inconsistent"))

    tap = entry.get("encoding", {}).get("tapering", {})
    hf_tap = tap.get("hf_tapered_state")
    if hf_tap is not None and all(x in (0, 1) for x in hf_tap):
        pass  # valid
    elif hf_tap is not None:
        print(_warn(f"{path.name}: hf_tapered_state contains non-binary values: {hf_tap}"))

    if ok:
        n_q_orig = tap.get("original_num_qubits", "?")
        n_q_tap  = tap.get("tapered_num_qubits", "?")
        gap_str  = f"{gap:.4e} Ha" if gap else "N/A"
        trust_lv = entry.get("trust", {}).get("level", "?")
        print(_ok(f"{path.name}  [{n_q_orig}->{n_q_tap}q  gap={gap_str}  trust={trust_lv}]"))

    return ok


def manual_check(path: Path) -> bool:
    """Basic checks without jsonschema."""
    entry = json.loads(path.read_text())
    ok    = True
    for field in ("schema_version", "entry_id", "problem", "encoding",
                  "artifacts", "results", "provenance"):
        if field not in entry:
            print(_fail(f"{path.name}: missing required field '{field}'"))
            ok = False
    if ok:
        print(_ok(f"{path.name}  (manual check passed)"))
    return ok


def main() -> None:
    paths = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.json")))
        elif p.exists():
            paths.append(p)
        else:
            # glob patterns
            from glob import glob
            matches = [Path(m) for m in glob(str(p))]
            paths.extend(sorted(matches))

    if not paths:
        default_dir = REPO / "releases" / "v3" / "db"
        if default_dir.exists():
            paths = [p for p in sorted(default_dir.glob("*.json"))
                     if p.name != "README.md"]

    if not paths:
        print(_warn("No entry files found. Pass a path or run from repo root."))
        sys.exit(0)

    print(f"\n{BOLD}--- Validating {len(paths)} v3 entries ---{RESET}")
    passed = sum(validate_file(p) for p in paths)
    failed = len(paths) - passed
    print(f"\n{BOLD}Summary: {passed}/{len(paths)} passed{RESET}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
