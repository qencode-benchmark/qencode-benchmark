# scripts/migrate_v1_clean_validation.py
#!/usr/bin/env python3
"""
One-time migration utility for qencode-db v1 entries.

What it does (safe, non-destructive semantics):
- Freezes `validation.vqe` as canonical.
- Quarantines legacy or untrusted validation fields under `validation.legacy.*`:
    - validation.vqe_run           -> validation.legacy.vqe_run
    - validation.vqe_simple_search -> validation.legacy.vqe_simple_search
- Optionally promotes `validation.vqe_result` into `validation.vqe` if vqe is missing.
- Normalizes a few metadata fields (basis, mapping, ansatz).
- Appends an audit record to `provenance.migrations[]`.
- Validates output against schema_v1.json via jsonschema.

Usage:
  python scripts/migrate_v1_clean_validation.py \
    --db-dir releases/v1/db \
    --schema schema_v1.json \
    --backup-dir /tmp/qencode-db-backup \
    --write

Dry run (default):
  python scripts/migrate_v1_clean_validation.py --db-dir releases/v1/db --schema schema_v1.json
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import jsonschema


MIGRATION_ID = "v1_clean_validation_2026-01-15"
SCRIPT_NAME = "scripts/migrate_v1_clean_validation.py"


Json = Dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha256_of_json(obj: Any) -> str:
    h = hashlib.sha256()
    h.update(stable_json_dumps(obj).encode("utf-8"))
    return h.hexdigest()


def ensure_dict(parent: Json, key: str) -> Json:
    v = parent.get(key)
    if isinstance(v, dict):
        return v
    parent[key] = {}
    return parent[key]


def deep_get(d: Json, path: Iterable[str]) -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def deep_set(d: Json, path: Iterable[str], value: Any) -> None:
    path = list(path)
    if not path:
        raise ValueError("Empty path")
    cur: Any = d
    for p in path[:-1]:
        if not isinstance(cur, dict):
            raise TypeError(f"Non-dict encountered while setting {'.'.join(path)}")
        cur = ensure_dict(cur, p)
    if not isinstance(cur, dict):
        raise TypeError(f"Non-dict encountered while setting {'.'.join(path)}")
    cur[path[-1]] = value


def deep_pop(d: Json, path: Iterable[str]) -> Tuple[bool, Any]:
    path = list(path)
    if not path:
        return False, None
    cur: Any = d
    for p in path[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return False, None
        cur = cur[p]
    if not isinstance(cur, dict) or path[-1] not in cur:
        return False, None
    return True, cur.pop(path[-1])


def normalize_basis(basis: Optional[str]) -> Optional[str]:
    if not isinstance(basis, str) or not basis.strip():
        return None
    b = basis.strip().lower()
    b = b.replace("-", "").replace("_", "")
    if b in {"sto3g", "sto-3g", "sto_3g"}:
        return "sto3g"
    return basis.strip().lower()


def normalize_mapping(mapping: Optional[str]) -> Optional[str]:
    if not isinstance(mapping, str) or not mapping.strip():
        return None
    m = mapping.strip().lower()
    aliases = {
        "jw": "jordan_wigner",
        "jordan-wigner": "jordan_wigner",
        "jordan_wigner": "jordan_wigner",
        "bk": "bravyi_kitaev",
        "bravyi-kitaev": "bravyi_kitaev",
        "bravyi_kitaev": "bravyi_kitaev",
    }
    return aliases.get(m, m)


def normalize_ansatz_type(ansatz_type: Optional[str]) -> Optional[str]:
    if not isinstance(ansatz_type, str) or not ansatz_type.strip():
        return None
    a = ansatz_type.strip().lower()
    aliases = {
        "uccsd": "uccsd",
        "hardware_efficient": "hardware_efficient",
        "hardware-efficient": "hardware_efficient",
        "he": "hardware_efficient",
        "geom": "geom",
    }
    return aliases.get(a, a)


def as_int(x: Any) -> Optional[int]:
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, str):
        s = x.strip()
        if s.isdigit():
            return int(s)
    return None


def as_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return None
    return None


@dataclass
class MigrationResult:
    changed: bool
    before_sha256: str
    after_sha256: str
    reasons: Tuple[str, ...]


def promote_vqe_result_to_vqe(validation: Json) -> Tuple[bool, str]:
    """
    If validation.vqe is missing but validation.vqe_result exists, create validation.vqe
    by copying a minimal canonical subset.
    """
    if isinstance(validation.get("vqe"), dict):
        return False, "validation.vqe already present"

    vqe_result = validation.get("vqe_result")
    if not isinstance(vqe_result, dict):
        return False, "no validation.vqe_result to promote"

    best_energy = as_float(vqe_result.get("best_energy"))
    if best_energy is None:
        return False, "validation.vqe_result.best_energy missing/unparseable"

    vqe: Json = {}
    vqe["best_energy"] = best_energy

    for k in ("method", "chosen_mode", "success", "message", "computed_utc", "units"):
        if k in vqe_result:
            vqe[k] = vqe_result.get(k)

    # If missing, set defaults consistent with repo conventions
    vqe.setdefault("units", "hartree_like")
    vqe.setdefault("computed_utc", utc_now_iso())

    validation["vqe"] = vqe
    return True, "promoted validation.vqe_result -> validation.vqe"


def quarantine_legacy_validation(validation: Json) -> Tuple[bool, Tuple[str, ...]]:
    changed = False
    reasons = []

    legacy = ensure_dict(validation, "legacy")

    for key in ("vqe_run", "vqe_simple_search"):
        if key in validation:
            legacy[key] = validation.pop(key)
            changed = True
            reasons.append(f"moved validation.{key} -> validation.legacy.{key}")

    return changed, tuple(reasons)


def normalize_entry_metadata(entry: Json) -> Tuple[bool, Tuple[str, ...]]:
    changed = False
    reasons = []

    problem = entry.get("problem")
    settings = entry.get("settings")

    if not isinstance(problem, dict) or not isinstance(settings, dict):
        return False, ("problem/settings missing or not objects",)

    chemistry = ensure_dict(settings, "chemistry")
    mapping = ensure_dict(settings, "mapping")
    ansatz = ensure_dict(settings, "ansatz")

    # Basis normalization
    pb = normalize_basis(problem.get("basis"))
    cb = normalize_basis(chemistry.get("basis"))
    target_basis = pb or cb
    if target_basis:
        if pb != target_basis:
            problem["basis"] = target_basis
            changed = True
            reasons.append("normalized problem.basis")
        if cb != target_basis:
            chemistry["basis"] = target_basis
            changed = True
            reasons.append("normalized settings.chemistry.basis")

    # Mapping normalization (keep problem.mapping aligned with settings.mapping.type)
    pm = normalize_mapping(problem.get("mapping"))
    mt = normalize_mapping(mapping.get("type"))
    target_mapping = pm or mt
    if target_mapping:
        if pm != target_mapping:
            problem["mapping"] = target_mapping
            changed = True
            reasons.append("normalized problem.mapping")
        if mt != target_mapping:
            mapping["type"] = target_mapping
            changed = True
            reasons.append("normalized settings.mapping.type")

    # Ansatz normalization
    at = normalize_ansatz_type(ansatz.get("type") or settings.get("ansatz_type"))
    if at and ansatz.get("type") != at:
        ansatz["type"] = at
        changed = True
        reasons.append("normalized settings.ansatz.type")

    reps = as_int(ansatz.get("reps") if "reps" in ansatz else settings.get("ansatz_reps"))
    if reps is not None:
        if ansatz.get("reps") != reps:
            ansatz["reps"] = reps
            changed = True
            reasons.append("normalized settings.ansatz.reps")
        if settings.get("ansatz_reps") != reps:
            settings["ansatz_reps"] = reps
            changed = True
            reasons.append("aligned settings.ansatz_reps")

    # Initial state default (don’t overwrite if present)
    if "initial_state" not in ansatz or not isinstance(ansatz.get("initial_state"), str) or not ansatz["initial_state"].strip():
        ansatz["initial_state"] = "hartree_fock"
        changed = True
        reasons.append("defaulted settings.ansatz.initial_state=hartree_fock")

    # Convenience mirror (don’t require, but keep aligned if present)
    if at and settings.get("ansatz_type") != at:
        settings["ansatz_type"] = at
        changed = True
        reasons.append("aligned settings.ansatz_type")

    return changed, tuple(reasons)


def append_provenance_migration(entry: Json, before_sha: str, after_sha: str, reasons: Tuple[str, ...]) -> Tuple[bool, str]:
    prov = entry.get("provenance")
    if not isinstance(prov, dict):
        return False, "provenance missing/not an object"

    migrations = prov.get("migrations")
    if migrations is None:
        prov["migrations"] = []
        migrations = prov["migrations"]

    if not isinstance(migrations, list):
        prov["migrations"] = []
        migrations = prov["migrations"]

    record = {
        "id": MIGRATION_ID,
        "script": SCRIPT_NAME,
        "ran_utc": utc_now_iso(),
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "reasons": list(reasons),
    }
    migrations.append(record)
    return True, "appended provenance.migrations record"


def migrate_one(entry: Json) -> MigrationResult:
    before_sha = sha256_of_json(entry)
    reasons = []

    # Normalize metadata (low risk, deterministic)
    changed_meta, why_meta = normalize_entry_metadata(entry)
    if changed_meta:
        reasons.extend(why_meta)

    # Validation canonicalization
    validation = entry.get("validation")
    if isinstance(validation, dict):
        promoted, why_promote = promote_vqe_result_to_vqe(validation)
        if promoted:
            reasons.append(why_promote)

        changed_legacy, why_legacy = quarantine_legacy_validation(validation)
        if changed_legacy:
            reasons.extend(why_legacy)

        # If vqe exists, ensure minimal sanity types without being opinionated.
        vqe = validation.get("vqe")
        if isinstance(vqe, dict):
            be = as_float(vqe.get("best_energy"))
            if be is not None and vqe.get("best_energy") != be:
                vqe["best_energy"] = be
                reasons.append("coerced validation.vqe.best_energy to float")
            vqe.setdefault("units", "hartree_like")
            vqe.setdefault("computed_utc", utc_now_iso())

    after_sha = sha256_of_json(entry)

    changed = before_sha != after_sha
    if changed:
        appended, _ = append_provenance_migration(entry, before_sha, after_sha, tuple(reasons))
        if appended:
            after_sha = sha256_of_json(entry)

    return MigrationResult(
        changed=changed,
        before_sha256=before_sha,
        after_sha256=after_sha,
        reasons=tuple(reasons),
    )


def iter_json_files(db_dir: Path, skip_index: bool) -> Iterable[Path]:
    for p in sorted(db_dir.rglob("*.json")):
        if skip_index and p.name == "index.json":
            continue
        yield p


def load_json(path: Path) -> Json:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Json) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate(schema: Json, instance: Json, path_hint: str) -> Optional[str]:
    try:
        jsonschema.validate(instance=instance, schema=schema)
        return None
    except jsonschema.ValidationError as e:
        return f"{path_hint}: {e.message}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="Directory containing v1 JSON entries (e.g. releases/v1/db)")
    ap.add_argument("--schema", required=True, help="Path to schema_v1.json")
    ap.add_argument("--write", action="store_true", help="Write changes to disk (default is dry-run)")
    ap.add_argument("--backup-dir", default=None, help="Optional dir to copy originals before writing")
    ap.add_argument("--skip-index", action="store_true", help="Skip index.json (recommended)")
    args = ap.parse_args()

    db_dir = Path(args.db_dir)
    schema_path = Path(args.schema)
    backup_dir = Path(args.backup_dir) if args.backup_dir else None

    if not db_dir.exists():
        raise SystemExit(f"db-dir not found: {db_dir}")
    if not schema_path.exists():
        raise SystemExit(f"schema not found: {schema_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    total = 0
    changed = 0
    failed = 0

    for path in iter_json_files(db_dir, skip_index=args.skip_index):
        total += 1
        original = load_json(path)
        entry = copy.deepcopy(original)

        result = migrate_one(entry)

        err = validate(schema, entry, str(path))
        if err:
            failed += 1
            print(f"❌ INVALID after migration: {err}")
            continue

        if result.changed:
            changed += 1
            print(f"🛠️  {path.name}")
            for r in result.reasons[:10]:
                print(f"   - {r}")
            if len(result.reasons) > 10:
                print(f"   - ... +{len(result.reasons) - 10} more")

            if args.write:
                if backup_dir:
                    rel = path.relative_to(db_dir)
                    dst = backup_dir / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_text(json.dumps(original, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                write_json(path, entry)
        else:
            print(f"✅ {path.name} (no change)")

    print("\nSummary")
    print(f"  total:   {total}")
    print(f"  changed: {changed}")
    print(f"  failed:  {failed}")
    print(f"  mode:    {'WRITE' if args.write else 'DRY-RUN'}")
    if backup_dir:
        print(f"  backups: {backup_dir}")


if __name__ == "__main__":
    main()

