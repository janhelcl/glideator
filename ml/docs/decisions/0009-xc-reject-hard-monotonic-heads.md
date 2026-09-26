# 0009 — Do not use hard monotonic output heads as the XC candidate baseline

Status: Accepted
Date: 2026-09-07

## Context

The XC targets `XC0` through `XC100` are nested events, so monotonic probabilities are semantically attractive. The migrated multilabel head does not guarantee monotonicity and the accepted no-CrossNet baseline still shows a small rate of threshold inversions.

Two structural alternatives were tested on benchmark `xc-temporal-2024-jan-nov-v1`:

1. a scalar ordinal head with one latent XC-strength score and ordered global thresholds;
2. an adaptive monotonic head with one feature-conditioned base logit and feature-conditioned positive cumulative gaps between thresholds.

Both guarantee zero monotonicity violations by construction.

## Decision

Keep the independent multilabel output head as the XC candidate baseline for now.

Do not continue tuning the tested scalar ordinal or adaptive cumulative-gap monotonic heads. Future hard-monotonic output work should require a materially different formulation, not just more seeds or width tuning of these heads.

The accepted structural baseline therefore remains:

- no CrossNet (`cross_layers: 0`);
- shared parallel deep tower;
- fusion tower `[64, 32]`;
- eleven independent sigmoid threshold heads.

## Why

The scalar ordinal head eliminated inversions but caused a large loss in calibration and discrimination, showing that a single latent XC-strength axis is too restrictive.

The adaptive monotonic head restored threshold-specific feature dependence, but still regressed against the no-CrossNet multilabel baseline on every primary predictive metric in the matched seed-42 run:

- macro BCE: `0.16209` vs `0.15982`;
- macro Brier: `0.04912` vs `0.04848`;
- macro ROC-AUC: `0.93601` vs `0.93944`;
- monotonic violation rate: `0.0000` vs `0.0199`.

Both models have `64,267` trainable parameters, so the regression is attributable to output parameterization rather than model size.

The experiment's acceptance bar was to match or improve calibration/discrimination while driving violations to zero. The adaptive head met only the monotonicity half of that bar.

Because the predictive regression is consistent across BCE, Brier and AUC and the hypothesis was already a direct response to the rejected ordinal result, another seed sweep has low expected value. The result is treated as a structural rejection rather than a stochastic near-tie.

## Consequences

- The no-CrossNet multilabel model remains the architecture baseline for the next phase.
- Small monotonicity violations are tolerated as a secondary metric rather than eliminated at the cost of predictive quality.
- The legacy monotonicity penalty remains available as a soft regularizer, but hard monotonicity is not a requirement for promotion.
- Next experiments should focus on representation/capacity and optimization around the no-CrossNet baseline rather than output-head constraints.
- The ordinal and adaptive-monotonic implementations/configs may remain in the repository as documented rejected experiments, but should not be promoted or tuned further without a new hypothesis.

## Evidence

- Adaptive monotonic MLflow run: `4753c267f3f447cb8eb19a2f8e406ff8` (`rumbling-mink-438`).
- Adaptive artifacts: `outputs/xc/architecture/adaptive-monotonic/`.
- Baseline config: `configs/xc/architecture/no_cross.yaml`.
- Adaptive config: `configs/xc/architecture/adaptive_monotonic.yaml`.
- Model notes: `docs/xc/models/ordinal.md`, `docs/xc/models/adaptive-monotonic.md`.
- Related decision: [ADR 0008](0008-xc-remove-crossnet-from-candidate-baseline.md).
