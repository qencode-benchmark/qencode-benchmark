# QEncode

QEncode is a reproducible benchmarking platform for evaluating quantum algorithms.

The platform provides a standardized benchmark suite, automated execution pipelines, certified benchmark results, workflow evaluation, and interactive analysis tools for quantum computing research.

## Motivation

Quantum algorithm evaluation is often inconsistent across studies due to differences in:

- encodings
- ansatz circuits
- noise models
- optimizers
- measurement strategies

QEncode addresses this by providing a **reproducible benchmarking framework** for evaluating algorithm configurations in a consistent way.

## Core Features

### Standard Benchmark Suite
A curated benchmark suite for quantum chemistry workloads.

### Automated Execution
Benchmark experiments run through a reproducible execution pipeline.

### Certified Results
Benchmark outputs are classified as:

- Experimental
- Validated
- Certified

### Workflow Evaluation
Compare complete algorithm strategies rather than individual parameters.

### Interactive Analysis
Explore benchmark results through comparison tools and dashboards.

## Benchmark Suite v1

The first benchmark suite evaluates small quantum chemistry systems.

| Molecule | Basis | Active Space |
|--------|--------|--------|
| H2 | STO-3G | (2,2) |
| BeH2 | STO-3G | (4,4) |

Supported encodings:

- Jordan–Wigner
- Bravyi–Kitaev
- Parity

Supported ansatz:

- UCCSD
- Hardware Efficient Ansatz

Execution modes:

- ideal simulation
- shot-based simulation
- noisy simulation

## Repository Structure
