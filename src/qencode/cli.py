"""``qencode`` command line.

Subcommands are thin: each one hands straight to the module that already implements it,
so there is exactly one implementation of anything and the console entry point cannot
drift away from the scripts the documentation references.
"""
from __future__ import annotations

import argparse
import sys

from qencode import __version__
from qencode._paths import is_checkout, repo_root

_EPILOG = """\
examples:
  qencode run --molecule H2                    generate a benchmark entry
  qencode run --molecule LiH --mapping parity  a different qubit encoding
  qencode check                                is this environment reproducible?
  qencode resources --db releases/v4/db        fault-tolerant resource estimates
  qencode where                                what checkout is in use

`qencode run` passes every unrecognised option through to the pipeline, so
`qencode run --help` prints the full list.
"""


def _cmd_run(argv):
    from qencode.pipeline import generate_entry_v4
    sys.argv = ["qencode run"] + argv
    return generate_entry_v4.main()


def _cmd_check(argv):
    try:
        from qencode.tools import check_reproducibility as chk
    except ImportError:
        print("The reproducibility checker needs the repository checkout "
              "(tools/check_vqe_reproducibility.py).", file=sys.stderr)
        return 1
    sys.argv = ["qencode check"] + argv
    return chk.main()


def _cmd_resources(argv):
    try:
        from qencode.tools import estimate_ft_resources as ft
    except ImportError:
        print("Resource estimation needs the repository checkout "
              "(tools/estimate_ft_resources.py).", file=sys.stderr)
        return 1
    sys.argv = ["qencode resources"] + argv
    return ft.main()


def _cmd_where(argv):
    root = repo_root()
    print("qencode %s" % __version__)
    if root is None:
        print("running from an installed package; no checkout found")
        print("entry generation works, but the git commit recorded in an entry will be")
        print("null. Set QENCODE_REPO or run from a clone for full provenance.")
    else:
        print("checkout: %s" % root)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(
        prog="qencode",
        description="Reproducible VQE quantum chemistry benchmarking.",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--version", action="version", version="qencode %s" % __version__)
    sub = ap.add_subparsers(dest="cmd")
    for name, help_text in (
            ("run", "generate a benchmark entry"),
            ("check", "check this environment for reproducibility"),
            ("resources", "fault-tolerant resource estimates for stored entries"),
            ("where", "report which checkout is in use"),
    ):
        sub.add_parser(name, help=help_text, add_help=False)

    if not argv:
        ap.print_help()
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in ("-h", "--help"):
        ap.print_help()
        return 0
    if cmd == "--version":
        print("qencode %s" % __version__)
        return 0

    handlers = {"run": _cmd_run, "check": _cmd_check,
                "resources": _cmd_resources, "where": _cmd_where}
    if cmd not in handlers:
        ap.print_help()
        print("\nunknown command: %s" % cmd, file=sys.stderr)
        return 2
    return handlers[cmd](rest) or 0


if __name__ == "__main__":
    sys.exit(main())
