"""Locate the repository and its data files, whether running from a clone or installed.

The pipeline was written to live inside a git checkout: it read the molecule catalogue
and the requirements pins by walking up from ``__file__``, and asked git for the commit
that produced an entry. None of that holds once the package is installed from a wheel,
so this module makes the three cases explicit instead of assuming one of them.

Resolution order for the repository root:

1. ``QENCODE_REPO``, if set. An explicit answer always wins, and the cluster jobs and
   Docker image both set it.
2. A walk upward from this file looking for a repository marker. This is the case when
   running from a clone or an editable install.
3. ``None``. Running from a wheel with no checkout anywhere. Entry generation still works
   because the catalogue ships as package data, but the git commit recorded in an entry
   will be null and the environment-drift guard has no pins to compare against, so
   generation refuses unless explicitly overridden.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# A file that exists at the root of a QEncode checkout and nowhere else on the way up.
_MARKER = "molecules_v4.json"

_PKG_DATA = Path(__file__).resolve().parent / "data"


def repo_root() -> Optional[Path]:
    """The checkout this is running against, or None when installed without one."""
    env = os.environ.get("QENCODE_REPO")
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / _MARKER).is_file() and (parent / "releases").is_dir():
            return parent
    return None


def data_file(name: str) -> Optional[Path]:
    """A data file, preferring the checkout so a local edit is picked up.

    Falls back to the copy bundled in the wheel. Returns None if neither has it, which
    callers are expected to handle rather than crash on -- a missing signing key is a
    normal condition for anyone who is not us.
    """
    root = repo_root()
    if root is not None:
        candidate = root / name
        if candidate.is_file():
            return candidate
    bundled = _PKG_DATA / Path(name).name
    if bundled.is_file():
        return bundled
    return None


def default_out_dir() -> Path:
    """Where a generated entry lands when the caller does not say.

    Inside a checkout this is the versioned database, matching the historical default so
    documented commands keep working. Installed, it is the working directory, because
    writing into site-packages would be wrong.
    """
    root = repo_root()
    if root is not None:
        return root / "releases" / "v4" / "db"
    return Path.cwd()


def is_checkout() -> bool:
    return repo_root() is not None
