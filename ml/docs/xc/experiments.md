# XC GPU and architecture experiments

This note tracks the active XC experiment sequence after migrating the production model family into the reproducible `glideator_ml.xc` pipeline. Run-level metrics belong in MLflow; durable conclusions are recorded in `docs/decisions/`.

## Settled experiment policy

### GPU batch size

The RTX 3090 profile flattened quickly while using very little VRAM. Batch 8,192 reached at least 95% of peak measured throughput while retaining 23 optimizer steps per epoch, versus only 3 at the maximum-throughput batch of 65,536.

**Current policy: batch size 8,192.** See [ADR 0007](../decisions/0007-xc-gpu-batch-policy.md).

The path appears transfer-bound rather than compute- or memory-bound, but an estimated fit epoch already takes only about 2.6 seconds, so input-pipeline optimization is deferred.

### Training budget

Architecture screening uses:

- batch size: `8192`;
- learning rate: `0.001`;
- max epochs: `200`;
- patience: `40` epochs;
- optimizer/objective/regularization otherwise unchanged unless the experiment explicitly targets them.

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

**Structural decision: `cross_layers: 0`.** See [ADR 0008](../decisions/0008-xc-remove-crossnet-from-candidate-baseline.md).

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

## Completed representation/capacity screen

The accepted no-CrossNet baseline feeds both the raw per-time input and a learned shared per-time encoder into fusion. The refinement screen kept the benchmark, optimizer, batch size, site embedding and multilabel head fixed while changing one representation/capacity hypothesis at a time.

Configs remain under `configs/xc/architecture/refinement/` as reproducible experiment records:

| Config | Change | Status |
| --- | --- | --- |
| `control.yaml` | shared encoder `[128, 64, 32]` | comparison control |
| `no_raw_skip.yaml` | remove raw per-time bypass | not promoted |
| `time_specific_encoder.yaml` | independent 09/12/15 encoders | not promoted |
| `smaller_encoder.yaml` | encoder `[64, 32]` | **promotion candidate** |
| `larger_encoder.yaml` | encoder `[256, 128, 64]` | not promoted |
| `smaller_fusion.yaml` | fusion `[32, 16]` | not promoted |
| `deeper_fusion.yaml` | fusion `[64, 64, 32]` | not promoted |

At seed 42, `smaller_encoder` produced the strongest overall refinement result:

| Metric | Smaller encoder |
| --- | ---: |
| Macro BCE | 0.15787 |
| Macro Brier | 0.04788 |
| Macro ROC-AUC | 0.94098 |
| Monotonic violation rate | 0.0270 |
| Trainable parameters | ~48.5k |
| Best epoch | 45 |

It improves all three primary predictive metrics while simplifying the shared per-time encoder substantially. The higher monotonic-violation rate remains a diagnostic, not a reason to impose a hard monotonic head that already regressed predictive quality.

## Active experiment: paired seed confirmation

Before changing the structural baseline, confirm `smaller_encoder` against the refinement control on paired seeds 42–46.

Use the reusable paired runner from `ml/`:

```bash
export ML_DATABASE_URL='postgresql://...'

glideator-ml confirm-seeds xc \
  --control-config configs/xc/architecture/refinement/control.yaml \
  --config configs/xc/architecture/refinement/smaller_encoder.yaml \
  --seeds 42 43 44 45 46
```

The runner:

- loads the XC dataset once and reuses the same prepared snapshot for every run;
- requires identical data and evaluation configs;
- verifies benchmark, dataset and evaluation fingerprints for every control/candidate pair;
- isolates artifacts under `seed-sweep/seed-<n>` so runs cannot overwrite one another;
- logs each model run to the existing MLflow experiment;
- writes `paired_comparison.json` with per-seed results, mean candidate-minus-control deltas, sample standard deviation of paired deltas and candidate win counts.

Promotion rule for this confirmation:

- mean macro BCE improves;
- mean macro Brier improves;
- mean macro ROC-AUC does not regress;
- paired win counts support the mean result rather than showing a single-seed outlier;
- parameter reduction is retained.

Monotonicity remains a reported secondary metric. If the smaller encoder passes this gate, it becomes the optimized architecture baseline for the next generic tuning step: site-embedding size.

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

## Planned generic optimization sequence

After the smaller-encoder confirmation:

1. site embedding size;
2. learning rate;
3. dropout / weight decay;
4. one smooth-activation check (`ReLU` vs `SiLU`);
5. freeze the optimized conventional MLP benchmark.

Only then start weather-specific architectures so their gains are measured against a properly tuned conventional baseline rather than an under-optimized MLP.
