# XC GPU and architecture experiments

This note tracks the active XC experiment sequence after migrating the production model family into the reproducible `glideator_ml.xc` pipeline. Run-level metrics belong in MLflow; durable conclusions are recorded in `docs/decisions/`.

## Settled experiment policy

### GPU batch size

The RTX 3090 profile flattened quickly while using very little VRAM. Batch 8,192 reached at least 95% of peak measured throughput while retaining 23 optimizer steps per epoch, versus only 3 at the maximum-throughput batch of 65,536.

**Current policy: batch size 8,192.** See [ADR 0007](../decisions/0007-xc-gpu-batch-policy.md).

The path appears transfer-bound rather than compute- or memory-bound, but an estimated fit epoch already takes only about 2.6 seconds, so input-pipeline optimization is deferred.

### Training budget

Moving from 2,048 to 8,192 reduces optimizer steps per epoch by roughly 4x. Architecture screening therefore uses:

- batch size: `8192`;
- learning rate: `0.001`;
- max epochs: `200`;
- patience: `40` epochs;
- optimizer/objective/regularization otherwise unchanged unless the architecture makes a term structurally unnecessary.

At about 23 steps per epoch, `patience: 40` preserves roughly the old stale-update budget.

### Benchmark

The warehouse currently ends on `2024-11-30`, so architecture experiments use benchmark `xc-temporal-2024-jan-nov-v1`:

- fit: before `2023-01-01`;
- validation/model selection: calendar year 2023;
- final evaluation: `2024-01-01` through `2024-11-30`;
- same feature contract and scaler behavior for every comparison.

Do not mix these Jan-Nov results with a future full-calendar-2024 benchmark without rerunning candidates.

## Completed first architecture sweep

The first sweep tested one structural change at a time from the migrated production-shaped control:

| Config | Structural question | Conclusion |
| --- | --- | --- |
| `control.yaml` | production-shaped reference | comparison control |
| `ordinal.yaml` | single latent ordinal XC axis | rejected; perfect monotonicity but materially worse BCE/Brier/AUC |
| `no_parallel.yaml` | remove parallel deep tower | small regression; keep the tower |
| `no_cross.yaml` | remove CrossNet | accepted structural baseline |
| `time_specific_cross.yaml` | separate CrossNets for 09/12/15 | small regression; sharing was not the CrossNet problem |
| `wider_fusion.yaml` | widen fusion tower | small regression; no evidence of a fusion-capacity bottleneck |

Because the no-CrossNet improvement was small, control and no-CrossNet were rerun with paired model seeds 42–46. No-CrossNet won BCE 4/5 times, Brier 4/5, AUC 3/5, and monotonicity 5/5. Mean AUC was effectively tied while calibration improved modestly, monotonicity violations dropped substantially, and parameter count fell from about 91k to 64k.

**Current structural baseline: `cross_layers: 0`.** See [ADR 0008](../decisions/0008-xc-remove-crossnet-from-candidate-baseline.md).

CrossNet remains only for compatibility with the served/reference family.

## Completed output-head experiments

### Scalar ordinal head

The scalar ordinal head guaranteed monotonic predictions but regressed materially on calibration and discrimination. Collapsing all XC thresholds onto one latent score was too restrictive.

Status: rejected.

### Adaptive monotonic head

The adaptive head replaced global ordinal cut-points with feature-conditioned positive cumulative logit gaps. This restored much of the lost flexibility while retaining perfect monotonicity.

On the matched seed-42 comparison against the no-CrossNet multilabel baseline:

| Metric | Adaptive monotonic | No-CrossNet |
| --- | ---: | ---: |
| Macro BCE | 0.16209 | 0.15982 |
| Macro Brier | 0.04912 | 0.04848 |
| Macro ROC-AUC | 0.93601 | 0.93944 |
| Monotonic violation rate | 0.0000 | 0.0199 |

The head met the zero-violation objective but regressed on all three primary predictive metrics. Because the predictive loss is consistent and this experiment directly addressed the ordinal head's known restriction, no seed sweep is warranted.

**Output-head decision: keep the independent multilabel head.** See [ADR 0009](../decisions/0009-xc-reject-hard-monotonic-heads.md).

The adaptive implementation and config remain as a documented rejected experiment rather than a promotion candidate.

## Current baseline

The architecture baseline for the next phase is therefore:

- no CrossNet (`cross_layers: 0`);
- shared parallel per-time deep tower `[128, 64, 32]`;
- fusion tower `[64, 32]`;
- 32-dimensional site embedding;
- eleven independent sigmoid XC-threshold heads;
- batch size `8192` with the normalized training budget above.

## Selection metrics

Do not select architecture on ROC-AUC alone. Compare at minimum:

- macro BCE;
- macro Brier score;
- macro ROC-AUC;
- per-threshold BCE/Brier/AUC;
- monotonicity violations;
- best epoch and validation loss;
- parameter count and wall-clock training time.

For architectures that are close on predictive metrics, prefer the simpler model unless a meaningful XC-threshold region improves consistently.

The output-head question is now settled. Next experiments should tune representation/capacity and optimization around the no-CrossNet multilabel family rather than starting with another output constraint or a large mixed grid.
