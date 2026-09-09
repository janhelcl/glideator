# 0001 — Stable benchmark identity

**Status:** Accepted  
**Date:** 2026-08-30

## Context

Early S2S comparisons used a single seed for both the train/evaluation split and stochastic model training. Changing the model seed could therefore change the benchmark itself, making multi-seed architecture comparisons subtly incomparable.

Temporal benchmarks have the same identity problem if the cutoff moves without changing the benchmark label.

## Decision

Benchmark identity is separate from model randomness.

For held-out-pilot S2S comparisons:

- data.split_seed defines the deterministic pilot split;
- model.seed controls stochastic model fitting;
- comparable runs keep split_seed fixed while model.seed varies.

For temporal S2S comparisons:

- temporal_cutoff is part of benchmark identity;
- changing the cutoff requires a new benchmark_id.

Every run records benchmark_id and eval_set_fingerprint derived from the exact walk-forward evaluation events.

## Why

A benchmark must remain fixed while the model changes. Otherwise observed variance mixes model randomness with evaluation-set changes.

The explicit evaluation fingerprint also makes accidental mismatch visible even when two configs claim the same benchmark_id.

## Consequences

- Multi-seed comparisons require identical evaluation fingerprints.
- Benchmark changes are intentional, named changes.
- Legacy top-level seed remains only as a compatibility fallback for older configs.
