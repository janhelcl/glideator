# XC model catalogue

XC model pages document architecture-level hypotheses and serving implications. Benchmark results belong in MLflow; durable experiment-policy or promote/reject decisions belong in decision records.

## Models

| Model | Role | Status | Doc |
| --- | --- | --- | --- |
| Expanded production reference | migrated served-model shape and compatibility baseline | reference | [Expanded production reference](expanded-production-reference.md) |
| No-CrossNet | simplified production-shaped model | accepted structural baseline | [No-CrossNet](no-cross.md) |
| Ordinal head | single latent XC-strength axis with ordered thresholds | rejected | [Ordinal](ordinal.md) |
| Adaptive monotonic head | feature-conditioned cumulative monotonic logits | rejected | [Adaptive monotonic](adaptive-monotonic.md) |
| Jev 1.13 | hosted typed-probability challenger over semantic weather state | rejected | [Jev 1.13](jev.md) |
| Jev 1.13 raw + production sites | full numeric weather and named takeoff context ablation | rejected | [Jev raw + production sites](jev-raw-prod-sites.md) |

New architectures should be added here when they have a reproducible config and can be evaluated on the current XC benchmark.

Model pages intentionally avoid duplicating full current metric tables. MLflow and saved evaluation artifacts are the run-level source of truth. Durable conclusions that change future experiment policy should be recorded under `docs/decisions/`.
