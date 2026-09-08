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

**Decision:** promote the shared per-time encoder `[64, 32]`. See [ADR 0011](../decisions/0011-xc-promote-smaller-shared-encoder.md).

## Current conventional baseline

`configs/xc/baselines/conventional_mlp.yaml` is the canonical conventional baseline:

- no CrossNet (`cross_layers: 0`);
- raw per-time bypass retained;
- shared per-time encoder `[64, 32]`;
- fusion tower `[64, 32]`;
- site embedding dimension `32`;
- independent multilabel head;
- batch size `8192`.

Old architecture/refinement configs remain only as lightweight reproducibility records.

## Completed site-embedding screen

The seed-42 screen varied only site-embedding dimension:

| Embedding dim | Macro BCE ↓ | Macro Brier ↓ | Macro ROC-AUC ↑ | Mono rate ↓ | Best epoch | Parameters |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 0.16101 | 0.04866 | 0.93933 | 0.0123 | 117 | 36.4k |
| 16 | 0.15944 | 0.04828 | 0.93964 | 0.0286 | 84 | 40.4k |
| 32 | **0.15787** | **0.04788** | 0.94098 | 0.0270 | 45 | 48.5k |
| 64 | 0.15833 | 0.04790 | **0.94156** | 0.0205 | 42 | 64.7k |

The 32-dimensional control is the best probabilistic fit. Going to 64 dimensions buys only `+0.00058` ROC-AUC while slightly worsening BCE/Brier and adding roughly 16k parameters. Smaller embeddings lose on all three primary predictive metrics.

**Decision:** keep `site_embedding_dim: 32` and close embedding-size tuning. See [ADR 0012](../decisions/0012-xc-keep-32d-site-embedding.md).

## Active experiment: training and regularization screen

### Hypothesis

The conventional architecture is now stable enough to tune optimization without confounding architecture choices. The first screen is intentionally one-factor-at-a-time around the locked 32-dimensional conventional baseline.

| Config | Learning rate | L2 penalty | Dropout | Role |
| --- | ---: | ---: | ---: | --- |
| `control.yaml` | 0.001 | 1e-9 | 0.00 | control |
| `lr_5e-4.yaml` | 0.0005 | 1e-9 | 0.00 | slower LR |
| `lr_2e-3.yaml` | 0.002 | 1e-9 | 0.00 | faster LR |
| `lr_3e-3.yaml` | 0.003 | 1e-9 | 0.00 | faster LR / bracket |
| `l2_1e-7.yaml` | 0.001 | 1e-7 | 0.00 | mild L2 |
| `l2_1e-6.yaml` | 0.001 | 1e-6 | 0.00 | stronger L2 |
| `dropout_005.yaml` | 0.001 | 1e-9 | 0.05 | mild dropout |
| `dropout_010.yaml` | 0.001 | 1e-9 | 0.10 | stronger dropout |

Dropout is opt-in and is applied after hidden activations in both the shared per-time encoder and the fusion tower. `dropout: 0.0` preserves the legacy module layout and behavior.

The trainer already has an explicit L2 penalty, so this screen varies `l2_lambda` rather than changing optimizer semantics at the same time. Adam remains fixed. If explicit L2 looks useful, AdamW can still be tested later as a separate optimizer hypothesis.

### Sweep runner

`glideator-ml sweep xc` loads the XC dataset once, runs every config against the same prepared snapshot, verifies benchmark/dataset/evaluation identity, keeps each run's artifacts isolated and writes a machine-readable `sweep_summary.json`.

Run from `ml/`:

```bash
export ML_DATABASE_URL='postgresql://...'

glideator-ml sweep xc \
  --configs \
    configs/xc/optimization/training/control.yaml \
    configs/xc/optimization/training/lr_5e-4.yaml \
    configs/xc/optimization/training/lr_2e-3.yaml \
    configs/xc/optimization/training/lr_3e-3.yaml \
    configs/xc/optimization/training/l2_1e-7.yaml \
    configs/xc/optimization/training/l2_1e-6.yaml \
    configs/xc/optimization/training/dropout_005.yaml \
    configs/xc/optimization/training/dropout_010.yaml \
  --output-dir outputs/xc/optimization/training/screen
```

### Selection rule

Screen seed 42 first. Compare at minimum:

- macro BCE;
- macro Brier score;
- macro ROC-AUC;
- per-threshold BCE/Brier/AUC, especially XC50–XC100;
- monotonicity violations;
- best epoch and validation loss;
- parameter count and wall-clock training time.

Do not seed-sweep every candidate. Pick the strongest learning-rate setting and strongest regularization setting. If both independently help, run one combined follow-up config using those two settings. Then promote at most one final candidate to paired seeds 42–46 against `control.yaml` using `glideator-ml confirm-seeds`.

For close candidates, prefer the configuration with better BCE/Brier unless an AUC change is clearly meaningful and consistent in the harder XC thresholds.

## Planned conventional optimization sequence

After this screen:

1. combine the winning LR and regularizer only if both independently help;
2. paired seed confirmation of the final training config;
3. one smooth-activation check (`ReLU` vs `SiLU`);
4. freeze the optimized conventional MLP benchmark.

Only then start weather-specific architectures so any gains are measured against a properly tuned conventional baseline.
