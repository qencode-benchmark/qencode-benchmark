# Submissions (v1)

This document defines how external users can submit benchmark results for validation and (optionally) inclusion in QEncode public datasets.

Submissions are designed for **algorithm researchers**: simple to create, easy to validate, and reproducible.

Commercial/onboarding links:

- Pricing / certification: https://www.qencode-benchmark.org/pricing
- Apply for access: https://www.qencode-benchmark.org/apply
- Contact: quencodebenchmark@gmail.com

---

## Submission format

Submissions use the JSON schema:

- `schema/submission_v1.json`

At a high level, a submission includes:

- **suite identity** (name + version)
- **submitter metadata**
- the **benchmark entry JSON** (schema v2)

---

## Validate a submission (recommended first step)

```bash
python scripts/validate_submission.py submission.json
```

If validation succeeds, the script exits with code 0 and prints a short summary. If it fails, it prints a readable error list and exits non-zero.

---

## Submit a result

```bash
python scripts/submit_result.py submission.json
```

This copies the validated submission into:

- `datasets/submissions/v1/`

It does not automatically publish anything; it just stages the submission in a canonical place so it can be reviewed or bundled into a dataset release later.

---

## Notes on eligibility

Passing submission validation does **not** automatically imply leaderboard eligibility.

Leaderboard eligibility is defined in:

- `docs/LEADERBOARD_RULES_V1.md`

Benchmark methodology is defined in:

- `docs/BENCHMARK_SPECIFICATION_V1.md`

