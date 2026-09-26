# 0017 — Reject the shared pressure-level MLP

Status: Accepted
Date: 2026-09-26

## Context

ADRs 0014 and 0015 closed the vertical Conv1D family after seed-42 improvements
failed paired-seed confirmation. The next experiment tested a different vertical
inductive bias without convolution or attention: apply one shared MLP `[16, 8]`
to `[u, v, T, RH, z]` at each of 13 ordered pressure levels, flatten the tokens
in canonical 1000→500 hPa order, and project them to a 32-dimensional profile
embedding.

The branch was additive to the frozen conventional model. Its raw per-time
bypass, shared `[64, 32]` MLP, fusion tower, site embedding, output head,
dropout, optimizer policy, data, and benchmark remained unchanged. A coherent
BCE/Brier improvement without a material ROC-AUC regression was required at
seed 42 before paired confirmation.

## Decision

Reject the shared pressure-level MLP after the seed-42 screen. Do not run seeds
43–46, tune the level-encoder width, add AGL/masking, or introduce attention on
top of this encoder.

Keep the implementation, config, tests, and model page as a reproducible
negative experiment. The frozen conventional MLP remains the XC promotion
baseline.

## Why

| Metric | Conventional MLP | Shared level MLP | Delta (candidate − control) |
| --- | ---: | ---: | ---: |
| Macro BCE ↓ | **0.15686** | 0.15794 | +0.00108 |
| Macro Brier ↓ | **0.04762** | 0.04785 | +0.00023 |
| Macro ROC-AUC ↑ | 0.94206 | **0.94233** | +0.00027 |
| Monotonic violation rate ↓ | **0.00140** | 0.00209 | +0.00069 |
| Best epoch | 86 | 86 | — |
| Parameters | 48,523 | 58,259 | +9,736 |

The candidate worsened both primary calibration metrics: BCE increased by about
0.69% and Brier by about 0.48%. Its ROC-AUC improvement was only about 0.03%,
while monotonic violations increased by roughly 49% and parameter count by
about 20%. The identical best epoch gives no indication that a different early
stopping point explains the result.

This fails the pre-specified screen. Paired-seed confirmation is reserved for
candidates with a coherent seed-42 signal and is not justified by a tiny,
isolated ranking improvement.

## Consequences

- `conventional_mlp.yaml` remains the promotion reference.
- `shared_level_mlp.yaml` remains available only for reproducibility.
- Do not continue the level-MLP branch with attention, AGL/masking, or width
  sweeps.
- Stop weather-profile architecture exploration for now and prioritize the
  combined comparison of the frozen conventional MLP against the actually
  served ONNX artifact.

## Evidence

- Benchmark: `xc-temporal-2024-jan-nov-v1`
- Seed: 42
- Candidate config: `configs/xc/architecture/weather_profiles/shared_level_mlp.yaml`
- Candidate report: `outputs/xc/architecture/weather-profiles/shared-level-mlp/evaluation.json`
- Model page: [Shared pressure-level MLP](../xc/models/shared-level-mlp.md)
