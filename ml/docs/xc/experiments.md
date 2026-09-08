# XC experiments

This note tracks the active XC experiment sequence after migrating the production model family into the reproducible `glideator_ml.xc` pipeline. Run-level metrics belong in MLflow; durable conclusions live in `docs/decisions/`.

## Fixed experiment policy

Architecture and optimization comparisons currently use:

- benchmark: `xc-temporal-2024-jan-nov-v1`;
- fit rows: before `2023-01-01`;
- validation/model selection: calendar year 2023;
- final evaluation: `2024-01-01` through `2024-11-30`;
- batch size: `8192`;
- learning rate: `0.001` unless the experiment explicitly targets it;
- max epochs: `200`;
- patience: `40`;
- identical feature contract and scaler behavior across candidates.

The warehouse currently ends on `2024-11-30`; do not mix these results with a future full-calendar-2024 benchmark without rerunning candidates.

## Settled architecture decisions

### GPU batch size

Batch 8,192 reached at least 95% of peak measured RTX 3090 throughput while retaining substantially more optimizer steps per epoch than larger batches.

**Decision:** use batch size `8192`. See [ADR 0007](../decisions/0007-xc-gpu-batch-policy.md).

### CrossNet

The no-CrossNet candidate beat the production-shaped control on paired seeds 42–46 often enough to establish a simpler structural baseline, while reducing parameters from roughly 91k to 64k.

**Decision:** `cross_layers: 0`. See [ADR 0008](../decisions/0008-xc-remove-crossnet-from-candidate-baseline.md).

CrossNet remains only for compatibility with the served/reference model family.

### Output head

Both scalar ordinal and adaptive monotonic heads eliminated monotonicity violations but regressed BCE, Brier and ROC-AUC.

**Decision:** keep eleven independent sigmoid heads. See [ADR 0009](../decisions/0009-xc-reject-hard-monotonic-heads.md).

### TabPFN-3 challenger

TabPFN-3 was tested both as an ordinal multiclass model and as eleven independent binary classifiers on the canonical XC contract.

**Decision:** do not replace the main XC model with TabPFN-3. See [ADR 0010](../decisions/0010-xc-reject-tabpfn3-as-main-model.md).

## Completed representation/capacity screen

The refinement screen kept the accepted no-CrossNet architecture fixed while changing one representation/capacity hypothesis at a time.

| Config | Change | Status |
| --- | --- | --- |
| `control.yaml` | shared encoder `[128, 64, 32]` | old comparison control |
| `no_raw_skip.yaml` | remove raw per-time bypass | rejected |
| `time_specific_encoder.yaml` | independent 09/12/15 encoders | rejected |
| `smaller_encoder.yaml` | encoder `[64, 32]` | **promoted** |
| `larger_encoder.yaml` | encoder `[256, 128, 64]` | rejected |
| `smaller_fusion.yaml` | fusion `[32, 16]` | rejected |
| `deeper_fusion.yaml` | fusion `[64, 64, 32]` | rejected |

The smaller encoder was confirmed against the old control on paired model seeds 42–46:

| Metric | Control mean | Smaller encoder mean | Candidate delta | Candidate wins |
| --- | ---: | ---: | ---: | ---: |
| Macro BCE ↓ | 0.16091 | 0.15764 | -0.00328 | 5/5 |
| Macro Brier ↓ | 0.04864 | 0.04785 | -0.00079 | 5/5 |
| Macro ROC-AUC ↑ | 0.93891 | 0.94098 | +0.00207 | 5/5 |
| Monotonic violation rate ↓ | 0.0165 | 0.0253 | +0.0088 | 1/5 |

The predictive result is clean: 5/5 wins on all three primary metrics while reducing trainable parameters from roughly 64k to 48.5k. The monotonicity regression remains a secondary diagnostic rather than a hard gate because hard-monotonic heads already showed a predictive penalty.

**Decision:** promote the shared per-time encoder `[64, 32]`. See [ADR 0011](../decisions/0011-xc-promote-smaller-shared-encoder.md).

## Current conventional baseline

`configs/xc/baselines/conventional_mlp.yaml` is now the canonical conventional baseline:

- no CrossNet (`cross_layers: 0`);
- raw per-time bypass retained;
- shared per-time encoder `[64, 32]`;
- fusion tower `[64, 32]`;
- site embedding dimension `32`;
- independent multilabel head;
- batch size `8192`.

Old architecture/refinement configs remain only as lightweight reproducibility records.

## Active experiment: site embedding size

### Hypothesis

The 32-dimensional learned site embedding may be oversized for roughly 250 sites, especially because latitude, longitude and altitude are already explicit features. Conversely, a larger embedding tests whether site identity still carries useful residual structure not captured by those geographic features.

Change only `site_embedding_dim`:

| Config | Embedding dim | Role |
| --- | ---: | --- |
| `configs/xc/optimization/site_embedding/embedding_8.yaml` | 8 | smaller challenger |
| `configs/xc/optimization/site_embedding/embedding_16.yaml` | 16 | smaller challenger |
| `configs/xc/baselines/conventional_mlp.yaml` | 32 | control |
| `configs/xc/optimization/site_embedding/embedding_64.yaml` | 64 | capacity check |

### Seed-42 screen

Run from `ml/`:

```bash
export ML_DATABASE_URL='postgresql://...'

for config in \
  configs/xc/optimization/site_embedding/embedding_8.yaml \
  configs/xc/optimization/site_embedding/embedding_16.yaml \
  configs/xc/baselines/conventional_mlp.yaml \
  configs/xc/optimization/site_embedding/embedding_64.yaml
do
  glideator-ml run xc --config "$config"
done
```

All four configs share the same benchmark and training contract; tests guard that challengers differ from the control only in embedding size, model name and artifact path.

### Promotion rule

Screen seed 42 first. Promote at most one challenger to paired seeds 42–46 using `glideator-ml confirm-seeds`.

Prefer a smaller embedding when BCE/Brier/AUC are effectively tied. Promote a larger embedding only if it produces a clear predictive gain that justifies the extra parameters.

## Selection metrics

Compare at minimum:

- macro BCE;
- macro Brier score;
- macro ROC-AUC;
- per-threshold BCE/Brier/AUC, especially XC50–XC100;
- monotonicity violations;
- best epoch and validation loss;
- parameter count and wall-clock training time.

For close candidates, prefer the simpler model unless a meaningful threshold region improves consistently.

## Planned conventional optimization sequence

After site embedding size:

1. learning rate;
2. dropout / AdamW weight decay;
3. one activation check (`ReLU` vs `SiLU`);
4. freeze the optimized conventional MLP benchmark.

Only then start weather-specific architectures so any gains are measured against a properly tuned conventional baseline.
