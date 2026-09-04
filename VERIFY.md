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

Bit-identical energies are guaranteed only on the reference pinned environment. Across
machines, what holds is that the entry still meets the certification threshold — for
gradient-free optimisers the two are genuinely different claims, and
[docs/VERIFY.md](docs/VERIFY.md) has the measurements.
