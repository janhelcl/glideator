# 0014 — Do not promote the plain vertical pressure-profile CNN

Status: Accepted
Date: 2026-09-08

## Context

The first weather-specific XC architecture added a shared Conv1D branch over the canonical 5 × 13 pressure profile while keeping the frozen conventional raw bypass, shared per-time MLP and fusion tower unchanged.

Seed 42 looked mildly positive, so the candidate was confirmed on paired model seeds 42–46 before any CNN hyperparameter tuning.

## Decision

Do not promote or tune the plain vertical-profile CNN as a replacement for the frozen conventional benchmark.

Keep the implementation as an experimental building block for sharper physics-aware hypotheses, but do not spend search budget on convolution width, depth or kernel-size sweeps in the raw pressure-index representation.

## Why

Across paired seeds 42–46 the candidate did not improve the primary metrics in expectation:

| Metric | Control mean | Vertical CNN mean | Mean delta (candidate − control) | Candidate wins |
| --- | ---: | ---: | ---: | ---: |
| Macro BCE ↓ | 0.156677 | 0.156742 | +0.000065 | 3/5 |
| Macro Brier ↓ | 0.047601 | 0.047611 | +0.000010 | 3/5 |
| Macro ROC-AUC ↑ | 0.941865 | 0.941676 | -0.000189 | 3/5 |
| Monotonic violation rate ↓ | 0.002076 | 0.006883 | +0.004807 | 1/5 |

The seed-42 BCE/Brier gain therefore did not replicate, while monotonicity was worse on average.

A plain convolution over pressure-level index also lacks several pieces of meteorological context that are plausibly more important than local adjacency alone: pressure spacing is non-uniform, some levels are below terrain, and absolute geopotential height is less directly relevant to a pilot than height relative to the launch/site.

## Consequences

- `vertical_conv.yaml` remains as the reproducible completed experiment.
- The frozen conventional MLP remains the promotion reference.
- Do not tune CNN width, depth or kernel size on the raw pressure-index representation.
- The next experiment may reuse the same CNN architecture only to isolate a physics-aware input representation: site-relative AGL plus an explicit above-ground validity mask.
- If the physics-aware representation also fails to improve the benchmark, move to a different profile encoder family rather than tuning the convolution.

## Evidence

Benchmark: `xc-temporal-2024-jan-nov-v1`, paired model seeds 42–46. Run-level artifacts and MLflow run IDs are recorded by the seed-comparison workflow.
