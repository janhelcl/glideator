# 0012 — Keep the 32-dimensional site embedding in the XC conventional baseline

Status: Accepted
Date: 2026-09-08

## Context

After promoting the smaller shared per-time encoder `[64, 32]`, the next isolated optimization question was site-embedding capacity. The conventional baseline used a 32-dimensional learned site embedding alongside explicit latitude, longitude and altitude features.

The seed-42 screen compared embedding dimensions 8, 16, 32 and 64 while holding the benchmark, architecture, optimizer, batch size and output head fixed.

## Decision

Keep `site_embedding_dim: 32` in the conventional XC baseline.

Do not spend further experiments interpolating embedding sizes before the training/regularization screen.

## Why

The screen showed a useful-capacity plateau around 32 dimensions:

| Embedding dim | Macro BCE ↓ | Macro Brier ↓ | Macro ROC-AUC ↑ | Monotonic violation rate ↓ | Best epoch | Parameters |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 0.16101 | 0.04866 | 0.93933 | 0.0123 | 117 | 36.4k |
| 16 | 0.15944 | 0.04828 | 0.93964 | 0.0286 | 84 | 40.4k |
| 32 | **0.15787** | **0.04788** | 0.94098 | 0.0270 | 45 | 48.5k |
| 64 | 0.15833 | 0.04790 | **0.94156** | 0.0205 | 42 | 64.7k |

Moving from 32 to 64 adds roughly 16k parameters and produces only a small ROC-AUC increase (`+0.00058`) while slightly worsening BCE (`+0.00046`) and Brier (`+0.00002`).

The 8- and 16-dimensional candidates are simpler but give up predictive quality on all three primary metrics.

## Consequences

- `configs/xc/baselines/conventional_mlp.yaml` remains the canonical baseline with `site_embedding_dim: 32`.
- Site-embedding tuning is closed unless a future architecture materially changes how site identity is represented.
- The next generic optimization step is learning rate and regularization.
- The 64-dimensional result remains useful evidence that discrimination can improve slightly beyond the probability-calibration optimum, but it is not enough to justify promotion for the current objective.
