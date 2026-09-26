# 0005 — Use a fixed temporal benchmark for XC

Status: Accepted
Date: 2026-09-06

## Context

The legacy XC feature-store notebook assigns validation rows with `ORDER BY RANDOM()` independently within each site and marks 20% as `is_validation`. Rebuilding the table therefore changes the evaluation set, and the random row split lets later dates contribute to training while earlier dates appear in validation.

That is useful as a rough training holdout, but it is not a stable benchmark for a model whose production job is to forecast future days.

## Decision

The first migrated XC benchmark is `xc-temporal-2024-v1`:

- source rows start at `2021-01-01`;
- the production-reference site domain remains `site_id <= 250`;
- training ends on `2023-12-31`;
- evaluation is the complete calendar year `2024-01-01` through `2024-12-31`;
- every evaluation site must have training history;
- the legacy `is_validation` column is ignored;
- the exact source values, feature order and evaluation rows are fingerprinted for every run.

Changing any of these benchmark semantics requires a new benchmark ID.

## Why

A temporal split matches the information boundary at inference time and is deterministic by construction. A complete held-out year also includes seasonality rather than evaluating a random mixture of dates from the same period used for fitting.

Keeping the first benchmark on the existing `features_with_target` source isolates migration of the training/evaluation machinery from a later redesign of labels, negative examples or weather sources.

## Consequences

- New XC runs are not numerically comparable with metrics reported from the old random `is_validation` split.
- Scalers are fitted only on the training window. Weather scaling continues to use the 12:00 feature slice, matching the legacy scaler notebook.
- Historical source backfills can still change row values; dataset and evaluation fingerprints make that change visible instead of silently redefining the benchmark.
- Production serving remains unchanged until a migrated run is compared directly with the currently served ONNX artifact.

## Evidence

- `analytics/training/data_prep/crate_fs_table.ipynb` — legacy random validation assignment.
- `analytics/training/fit_scalers.ipynb` — noon-only weather scaler fitting.
- `ml/configs/xc_production_reference.yaml` — executable benchmark definition.
