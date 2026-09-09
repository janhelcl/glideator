# 0015 — Stop the XC vertical Conv1D profile family

Status: Accepted
Date: 2026-09-09

## Context

ADR 0014 rejected the plain pressure-index Conv1D after its seed-42 improvement failed to replicate across paired seeds 42–46. One sharper follow-up kept that CNN architecture frozen and changed only its structured profile representation:

- replace absolute geopotential height with site-relative `z_AGL = geopotential_height - site_altitude`;
- fit AGL scaling only on valid above-terrain training/noon levels;
- derive an above-ground validity mask from GFS surface pressure;
- zero below-ground physical channels and append the mask as a sixth CNN channel.

Seed 42 improved BCE, Brier, ROC-AUC and monotonicity against both the plain CNN and the frozen conventional MLP, so the representation was confirmed on paired seeds 42–46 before any convolution hyperparameter tuning.

## Decision

Do not promote the AGL/mask vertical CNN. Stop the current Conv1D pressure-profile family rather than tuning its width, depth, kernel size or adding further coordinate channels to the same architecture.

The frozen conventional MLP remains the XC promotion baseline. The next weather-specific architecture should change the inductive bias, starting with a level-wise/shared-token encoder rather than another Conv1D variant.

## Why

Against the frozen conventional MLP, the five-seed confirmation did not reproduce the seed-42 gain:

| Metric | MLP mean | AGL/mask mean | Mean delta (AGL − MLP) | AGL wins |
| --- | ---: | ---: | ---: | ---: |
| Macro BCE ↓ | 0.156677 | 0.156987 | +0.000310 | 2/5 |
| Macro Brier ↓ | 0.047601 | 0.047635 | +0.000034 | 3/5 |
| Macro ROC-AUC ↑ | 0.941865 | 0.941867 | +0.000002 | 3/5 |
| Monotonic violation rate ↓ | 0.002076 | 0.005656 | +0.003580 | 2/5 |

Against the plain vertical CNN, the representation change also did not improve the primary losses:

| Metric | Plain CNN mean | AGL/mask mean | Mean delta (AGL − CNN) | AGL wins |
| --- | ---: | ---: | ---: | ---: |
| Macro BCE ↓ | 0.156742 | 0.156987 | +0.000245 | 2/5 |
| Macro Brier ↓ | 0.047611 | 0.047635 | +0.000024 | 2/5 |
| Macro ROC-AUC ↑ | 0.941676 | 0.941867 | +0.000191 | 4/5 |
| Monotonic violation rate ↓ | 0.006883 | 0.005656 | -0.001227 | 2/5 |

The small ROC-AUC signal versus the plain CNN is not accompanied by BCE/Brier improvement and does not clear the conventional promotion bar. It is therefore insufficient evidence to continue investing in this convolution family.

Both vertical-CNN screens produced attractive seed-42 results that disappeared under paired-seed confirmation. Future weather-specific architecture screens should continue to treat seed 42 only as a cheap filter, not promotion evidence.

## Consequences

- `conventional_mlp.yaml` remains the promotion reference.
- Keep `vertical_conv.yaml` and `vertical_conv_agl_mask.yaml` as reproducible negative experiments; do not delete them.
- Do not tune Conv1D channel widths, depth or kernel size.
- Do not add pressure/log-pressure coordinates as another incremental Conv1D experiment.
- Preserve the useful physics work (AGL derivation and above-ground masking) as potential inputs to a different profile encoder.
- The next vertical-profile experiment should test a different inductive bias, preferably a shared per-level encoder before considering level attention.

## Evidence

Benchmark: `xc-temporal-2024-jan-nov-v1`, paired model seeds 42–46. The multi-control confirmation compares the same AGL/mask candidate run for each seed against both the frozen conventional MLP and the plain vertical CNN. Run-level artifacts and MLflow run IDs are recorded by the seed-comparison workflow.