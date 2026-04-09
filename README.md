# QEncode - Quantum Algorithm Benchmarking Standard

QEncode is a benchmark standard and execution platform for reproducible quantum chemistry algorithm evaluation.

It combines:

- fixed benchmark definitions (molecules, basis, mappings, ansatz settings),
- managed execution and verification workflows,
- signed certification artifacts, and
- a public leaderboard filtered to certified entries.

## Why QEncode exists

Quantum benchmarking is often not directly comparable across teams because setups differ:

- molecule set and geometry choices,
- encoding and ansatz assumptions,
- optimizer and stopping conditions,
- hardware/noise and shot settings.

QEncode reduces this ambiguity with a fixed suite and reproducible outputs.

## Platform model

- Benchmark methodology is public.
- Managed execution, private benchmarking, and official certification are delivered through the website funnel.
- Official public leaderboard inclusion is tied to certified outputs and trust filtering.

## Official links

- Website: https://www.qencode-benchmark.org
- Leaderboard: https://www.qencode-benchmark.org/leaderboard
- Benchmark spec: https://www.qencode-benchmark.org/benchmark
- Documentation: https://www.qencode-benchmark.org/docs
- Pricing / certification: https://www.qencode-benchmark.org/pricing
- Apply for access: https://www.qencode-benchmark.org/apply
- Contact: quencodebenchmark@gmail.com

## Quick start (local technical run)

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the official suite pipeline:

```bash
python scripts/run_qencode_benchmark.py
```

Run one molecule:

```bash
python scripts/run_qencode_benchmark.py --molecule H2
```

For full environment setup and troubleshooting, see `docs/GETTING_STARTED.md`.

## Core CLI examples

Single benchmark:

```bash
python scripts/run_benchmark.py --molecule H2 --mapping JW --ansatz UCCSD --backend all
```

Matrix benchmark:

```bash
python scripts/run_matrix.py --matrix benchmarks/matrix_mvp.json
```

Comparison and ranking:

```bash
python scripts/compare.py --molecule H2
python scripts/rank.py --molecule H2
```

## Repository structure

- `benchmarks/standard/` - fixed suite definitions
- `datasets/` - leaderboard CSVs and release snapshots
- `releases/v2/db/` - generated benchmark entries
- `scripts/` - benchmark, comparison, leaderboard, and release tooling
- `docs/` - technical docs and project phases
- `website/` - Next.js marketing site and public leaderboard UI

## Notes for website alignment

- Public website CTAs prioritize `Apply for Access` and `Pricing`.
- `pricing` is the commercial entrypoint for certification services.
- Docs and repository links should target `qencode-benchmark/qencode-benchmark`.

## Additional docs

- Quick start: `docs/QUICK_START.md`
- Standard Suite v2: `docs/STANDARD_SUITE_V2.md`
- Leaderboard rules: `docs/LEADERBOARD_RULES_V1.md`
- Runtime/cache operations: `docs/RUNTIME_AND_CACHE.md`
- Phases overview: `docs/PHASES_OVERVIEW.md`
