## Quickstart (validate + build + trusted export + supply-chain)

From repo root:

```bash
python3 scripts/check_all.py --gap-threshold 0.01 \
  --stamp-env \
  --export-trusted --trusted-out-dir releases/v2/trusted \
  --trusted-require-gap-check --trusted-clean-out-dir \
  --supply-chain --manifest-only-json-entries --verify-entry-hashes

