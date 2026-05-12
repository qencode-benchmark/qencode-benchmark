# Verifying a QEncode Entry

See [docs/VERIFY.md](docs/VERIFY.md) for the full verification guide.

Quick reference:

```bash
python scripts/generate_entry_v3.py \
  --molecule HF \
  --basis 6-31g \
  --mapping parity \
  --ansatz-type uccsd \
  --multistart 10 \
  --seed 42
```

Compare `entry_hash_sha256` in the output with the value in
`releases/v3.1/db/<entry_id>.json`.
