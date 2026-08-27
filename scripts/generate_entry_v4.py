#!/usr/bin/env python3
"""Compatibility shim. The pipeline now lives in ``qencode.pipeline.generate_entry_v4``.

This path is referenced by the Dockerfile entrypoint, QUICKSTART, the README, CI and
several published posts, so it keeps working. New code should import the package.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from qencode.pipeline.generate_entry_v4 import *          # noqa: F401,F403,E402
from qencode.pipeline.generate_entry_v4 import main       # noqa: E402

if __name__ == "__main__":
    main()
