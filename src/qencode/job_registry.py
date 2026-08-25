"""
Phase 14: Job registry for suite runs — track pending/running/completed/failed/skipped_cached, enable resume.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from qencode.cache import compute_config_hash

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED_CACHED = "skipped_cached"


def _connect(registry_path: Path) -> sqlite3.Connection:
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(registry_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_registry(registry_path: Path) -> None:
    """Create the jobs table if it does not exist."""
    conn = _connect(registry_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                config_hash TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT,
                finished_at TEXT,
                duration_sec REAL,
                cache_hit INTEGER DEFAULT 0,
                error_message TEXT,
                entry_path TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def job_id_from_config(config: Dict[str, Any]) -> str:
    """Use config hash as job_id so it's deterministic and matches cache."""
    return compute_config_hash(config)


def get_status(registry_path: Path, job_id: str) -> Optional[Dict[str, Any]]:
    """Return current row for job_id or None."""
    conn = _connect(registry_path)
    try:
        row = conn.execute(
            "SELECT job_id, config_hash, status, started_at, finished_at, duration_sec, cache_hit, error_message, entry_path FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)
    finally:
        conn.close()


def ensure_pending_jobs(registry_path: Path, job_configs: List[Dict[str, Any]]) -> None:
    """Insert job_id for each config with status pending if not already present."""
    ensure_registry(registry_path)
    conn = _connect(registry_path)
    try:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for config in job_configs:
            # compute_config_hash already normalizes config deterministically
            jid = compute_config_hash(config)
            conn.execute(
                """
                INSERT OR IGNORE INTO jobs (job_id, config_hash, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (jid, jid, STATUS_PENDING, now),
            )
        conn.commit()
    finally:
        conn.close()


def get_pending_jobs(registry_path: Path) -> List[str]:
    """Return list of job_ids with status pending."""
    ensure_registry(registry_path)
    conn = _connect(registry_path)
    try:
        rows = conn.execute(
            "SELECT job_id FROM jobs WHERE status = ? ORDER BY job_id",
            (STATUS_PENDING,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def claim_next_job(registry_path: Path) -> Optional[str]:
    """
    Atomically claim one pending job — marks it running and returns its job_id.
    Returns None if no pending jobs remain.

    Safe for concurrent workers (multiple terminals or machines sharing the same
    registry file) because the UPDATE + rowcount check happens inside a single
    SQLite transaction with an exclusive write lock.
    """
    ensure_registry(registry_path)
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _connect(registry_path)
    try:
        # Fetch one pending job and claim it in a single atomic transaction.
        # SQLite serialises writers, so no two workers can claim the same row.
        conn.execute("BEGIN EXCLUSIVE")
        row = conn.execute(
            "SELECT job_id FROM jobs WHERE status = ? ORDER BY job_id LIMIT 1",
            (STATUS_PENDING,),
        ).fetchone()
        if row is None:
            conn.execute("ROLLBACK")
            return None
        job_id = row[0]
        conn.execute(
            "UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?",
            (STATUS_RUNNING, now, job_id),
        )
        conn.execute("COMMIT")
        return job_id
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def mark_running(registry_path: Path, job_id: str) -> None:
    """Set status to running and started_at."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _connect(registry_path)
    try:
        conn.execute(
            "UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?",
            (STATUS_RUNNING, now, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_completed(
    registry_path: Path,
    job_id: str,
    entry_path: Optional[Path] = None,
    duration_sec: Optional[float] = None,
    cache_hit: bool = False,
) -> None:
    """Set status to completed, optional entry_path and duration."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _connect(registry_path)
    try:
        conn.execute(
            """UPDATE jobs SET status = ?, finished_at = ?, duration_sec = ?, cache_hit = ?, entry_path = ? WHERE job_id = ?""",
            (STATUS_COMPLETED, now, duration_sec, 1 if cache_hit else 0, str(entry_path) if entry_path else None, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_failed(registry_path: Path, job_id: str, error_message: Optional[str] = None) -> None:
    """Set status to failed and optional error_message."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _connect(registry_path)
    try:
        conn.execute(
            "UPDATE jobs SET status = ?, finished_at = ?, error_message = ? WHERE job_id = ?",
            (STATUS_FAILED, now, error_message or "", job_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_pending(registry_path: Path, job_id: str, clear_error: bool = False) -> None:
    """Set status back to pending so job can be retried."""
    conn = _connect(registry_path)
    try:
        if clear_error:
            conn.execute(
                "UPDATE jobs SET status = ?, started_at = NULL, finished_at = NULL, duration_sec = NULL, error_message = '' WHERE job_id = ?",
                (STATUS_PENDING, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, started_at = NULL, finished_at = NULL, duration_sec = NULL WHERE job_id = ?",
                (STATUS_PENDING, job_id),
            )
        conn.commit()
    finally:
        conn.close()


def mark_skipped_cached(registry_path: Path, job_id: str, entry_path: Optional[Path] = None) -> None:
    """Set status to skipped_cached (Layer 1 cache hit)."""
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn = _connect(registry_path)
    try:
        conn.execute(
            "UPDATE jobs SET status = ?, finished_at = ?, cache_hit = 1, entry_path = ? WHERE job_id = ?",
            (STATUS_SKIPPED_CACHED, now, str(entry_path) if entry_path else None, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_jobs_by_status(registry_path: Path, status: str) -> List[str]:
    """Return list of job_ids with given status."""
    ensure_registry(registry_path)
    conn = _connect(registry_path)
    try:
        rows = conn.execute("SELECT job_id FROM jobs WHERE status = ? ORDER BY job_id", (status,)).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def summary(registry_path: Path) -> Dict[str, int]:
    """Return counts by status."""
    ensure_registry(registry_path)
    conn = _connect(registry_path)
    try:
        rows = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
        counts = {r[0]: r[1] for r in rows}
        for s in (STATUS_PENDING, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, STATUS_SKIPPED_CACHED):
            counts.setdefault(s, 0)
        return counts
    finally:
        conn.close()
