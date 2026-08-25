"""
Phase 14: Runtime helpers — timing and future instrumentation.

Used by profile_runtime and (in Phase 14b) for per-stage timing inside the pipeline.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def timer(label: str = "") -> Generator[list, None, None]:
    """Context manager that records elapsed time in seconds. Use for profiling."""
    t0 = time.perf_counter()
    result = [0.0]
    try:
        yield result
    finally:
        result[0] = time.perf_counter() - t0
