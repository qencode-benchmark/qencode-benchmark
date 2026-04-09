# artifacts/

This directory contains generated outputs from the QEncode benchmark pipeline.

These files are produced by running:

```bash
python scripts/run_qencode_benchmark.py
```

Key outputs:

- `benchmark_leaderboard.md` - human-readable leaderboard report
- `leaderboard_audit_v1.md` - audit log for certified entries
- `standard_suite_v1_report.md` - suite execution summary

These files are regenerated on each benchmark run and should not be edited manually.
