# 0013 — Freeze the optimized XC conventional benchmark

Status: Accepted
Date: 2026-09-08

## Context

The conventional XC model was intentionally optimized before starting weather-specific architecture work. After settling the no-CrossNet architecture, the `[64, 32]` shared per-time encoder, the `[64, 32]` fusion tower, a 32-dimensional site embedding and independent sigmoid heads, the remaining generic question was regularization and optimizer tuning.

A first seed-42 screen identified `dropout: 0.10` as the only change that improved BCE, Brier, ROC-AUC and monotonicity together. A final local screen tested nearby dropout values and the only mildly interesting LR/L2 interactions.

| Config | BCE ↓ | Brier ↓ | ROC-AUC ↑ | Mono rate ↓ | Best epoch |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dropout_010` | 0.15686 | 0.04762 | 0.94206 | 0.0014 | 86 |
| `dropout_0075` | 0.15760 | 0.04771 | 0.94175 | 0.0016 | 86 |
| `dropout_0125` | 0.15748 | 0.04771 | 0.94176 | 0.0012 | 86 |
| `dropout_015` | 0.15701 | 0.04760 | 0.94198 | 0.0006 | 86 |
| `dropout_010_l2_1e-6` | 0.15769 | 0.04779 | 0.94191 | 0.0012 | 86 |
| `dropout_010_lr_2e-3` | 0.15641 | 0.04772 | 0.94112 | 0.0025 | 31 |

The nearby dropout settings do not materially beat 0.10 across the primary predictive metrics. Extra L2 is harmful. Doubling the learning rate improves BCE but gives back Brier, ROC-AUC and monotonicity.

## Decision

Freeze `configs/xc/baselines/conventional_mlp.yaml` with:

- `cross_layers: 0`;
- raw per-time bypass retained;
- shared per-time MLP `[64, 32]`;
- fusion tower `[64, 32]`;
- `site_embedding_dim: 32`;
- independent multilabel sigmoid head;
- `dropout: 0.10`;
- learning rate `0.001`;
- L1/L2/monotonicity penalties `1e-9`;
- batch size `8192`.

Do not spend more runs tuning generic MLP capacity, dropout, learning rate or weight decay before weather-specific architecture experiments. New candidates must compare against this frozen config on the same benchmark contract.

## Why

The goal of the conventional pass was to remove obvious generic-model weaknesses, not to optimize seed-42 noise indefinitely. `dropout: 0.10` is the robust interior choice from the two-stage screen and gives the strongest overall balance of calibration, discrimination and monotonicity.

Freezing now makes improvements from subsequent experiments attributable to weather-specific inductive biases rather than moving baseline hyperparameters.

## Consequences

`conventional_mlp.yaml` is now the canonical control for weather-specific experiments. The optimization configs remain unchanged as reproducibility records of the path to this benchmark.

The next experiment family begins with a shared vertical pressure-profile encoder while retaining the raw and conventional MLP branches.

## Evidence

Benchmark: `xc-temporal-2024-jan-nov-v1`.

Reference seed-42 metrics for the frozen benchmark are BCE `0.15686`, Brier `0.04762`, ROC-AUC `0.94206`, monotonic violation rate `0.0014`, best epoch `86`.
