#!/usr/bin/env python3
"""Write the generated results table into docs/NOISY_TIER.md between its markers.

    python tools/fill_noisy_tier_doc.py

tests/test_noisy_tier.py fails when the document and the records disagree, so the
table in the document is never hand-edited.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import noisy_tier as nt  # noqa: E402

DOC = os.path.join(ROOT, "docs", "NOISY_TIER.md")
BEGIN, END = "<!-- TABLE:BEGIN -->", "<!-- TABLE:END -->"


def main():
    with open(DOC) as fh:
        doc = fh.read()
    i = doc.index(BEGIN) + len(BEGIN)
    j = doc.index(END)
    table = nt.markdown_table(nt.OUT_DIR)
    doc = doc[:i] + "\n" + table + "\n" + doc[j:]
    with open(DOC, "w") as fh:
        fh.write(doc)
    print("table written: %d lines" % (table.count("\n") + 1))


if __name__ == "__main__":
    main()
