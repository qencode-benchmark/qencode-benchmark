"""
Phase 15: Certification helpers — whether an entry is in the standard suite, manifest checks, etc.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from qencode.standard_suite import _entry_signature, expand_standard_suite, load_standard_suite


def is_entry_in_standard_suite(entry: Dict[str, Any], suite: Dict[str, Any]) -> bool:
    """True if entry (molecule, variant, basis, mapping, ansatz_type, reps) is in the suite's run grid."""
    sig = _entry_signature(entry)
    if sig is None:
        return False
    run_jobs, _ = expand_standard_suite(suite)
    for job in run_jobs:
        job_sig = (
            (job.get("molecule") or "").lower(),
            (job.get("variant") or "default").lower(),
            (job.get("basis") or "sto3g").lower(),
            job.get("mapping", ""),
            job.get("ansatz_type", ""),
            int(job.get("ansatz_reps") or 1),
        )
        if job_sig == sig:
            return True
    return False


def load_standard_suite_spec(suite_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load standard suite v1 spec for certification checks. Returns None if not found."""
    try:
        return load_standard_suite(suite_path)
    except Exception:
        return None
