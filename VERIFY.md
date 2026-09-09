# Verifying a QEncode entry

```bash
python scripts/verify_entry.py releases/v4/db/<entry_id>.json
```

Full guide, including the difference between `--mode strict` and `--mode certification`
and why that distinction exists: **[docs/VERIFY.md](docs/VERIFY.md)**.

If you are checking our work from your own machine rather than the reference environment,
this is the command you want:

```bash
python scripts/verify_entry.py <entry>.json \
    --mode certification --allow-dirty --allow-env-drift
```

### The strongest check: the reference environment

    docker pull ghcr.io/qencode-benchmark/qencode-reference:v4
    scripts/verify_in_reference.sh releases/v4/db/<entry>.json

A container image in which the result does not depend on the processor. Measured: six
entries generated on an AMD AVX2 machine and an Intel AVX-512 machine agree on none of six
outside it and on six of six inside it, differing by up to 6 mHa outside. Full account and
what it does not cover: **[docs/REFERENCE_ENVIRONMENT.md](docs/REFERENCE_ENVIRONMENT.md)**.

Bit-identical energies are guaranteed only on the reference pinned environment. Across
machines, what holds is that the entry still meets the certification threshold — for
gradient-free optimisers the two are genuinely different claims, and
[docs/VERIFY.md](docs/VERIFY.md) has the measurements.
