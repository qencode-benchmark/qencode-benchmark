# notebooks

## `score_your_vqe_result.ipynb`

You ran a VQE, you have an energy, and you want to know what it is worth. The notebook
answers that in one call: the gap against the exact ground state of your own active space,
which of the two thresholds it clears, how much margin it has, whether your optimiser and
ansatz make that margin fragile on another machine, and where the number would rank among
the published entries for the same molecule.

It needs `pip install qencode-benchmark` and nothing else — scoring imports no chemistry
stack, because the references for all 16 suite molecules ship inside the package as a
22 KB JSON table.

The only cell to edit is Step 1.

### What it deliberately does not do

- It does not certify anything. Certification is what the pipeline produces: a full run
  with recorded provenance, a content hash and a signature. A self-reported number can
  *meet the threshold*; it cannot be certified. See [`docs/TRUST_POLICY.md`](../docs/TRUST_POLICY.md).
- It refuses rather than guesses. A declared active space that does not match the
  reference raises, because a gap between two different problems is not a worse number,
  it is a meaningless one.
- It checks the variational principle before reporting a gap. An energy below the exact
  ground state means the problem solved was not the one intended, and that is said first.

### Re-running it

The committed copy carries executed outputs, so it reads correctly on GitHub without
being run. After changing it, execute it before committing — `tests/test_notebook.py`
fails if code cells have no execution count, or if any cell errored:

```bash
python -m venv /tmp/nbenv && /tmp/nbenv/bin/pip install nbformat nbconvert ipykernel
PYTHONPATH=src /tmp/nbenv/bin/jupyter nbconvert --to notebook --execute --inplace \
    notebooks/score_your_vqe_result.ipynb
```

Jupyter is deliberately not a CI dependency: the test checks the notebook's structure,
its outputs and every `qencode.*` name it calls, which is what actually breaks.
