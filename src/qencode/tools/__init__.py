"""Analysis tools, re-exported from the repository tools/ directory when running from a
checkout. They are kept at their published paths because CI, the QUICKSTART and several
posts reference them there."""
import os, sys
from qencode._paths import repo_root

_root = repo_root()
if _root is not None:
    _t = os.path.join(str(_root), "tools")
    if os.path.isdir(_t) and _t not in sys.path:
        sys.path.insert(0, _t)
