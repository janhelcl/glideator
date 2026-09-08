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

`configs/xc/baselines/conventional_mlp.yaml` is the canonical conventional architecture baseline:

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

## Completed training and regularization screen

The first seed-42 optimization screen changed one training axis at a time around the locked 32-dimensional conventional architecture.

| Config | BCE ↓ | Brier ↓ | ROC-AUC ↑ | Mono rate ↓ | Best epoch |
| --- | ---: | ---: | ---: | ---: | ---: |
| `control.yaml` | 0.15787 | 0.04788 | 0.94098 | 0.0270 | 45 |
| `lr_5e-4.yaml` | 0.15779 | 0.04781 | 0.94077 | 0.0324 | 98 |
| `lr_2e-3.yaml` | 0.15752 | 0.04796 | 0.94094 | 0.0287 | 34 |
| `lr_3e-3.yaml` | 0.15817 | 0.04804 | 0.94021 | 0.0265 | 22 |
| `l2_1e-7.yaml` | 0.15915 | 0.04819 | 0.94087 | 0.0290 | 45 |
| `l2_1e-6.yaml` | 0.15768 | 0.04784 | 0.94116 | 0.0283 | 45 |
| `dropout_005.yaml` | 0.15688 | 0.04768 | 0.94080 | 0.0089 | 46 |
| `dropout_010.yaml` | **0.15686** | **0.04762** | **0.94206** | **0.0014** | 86 |

`dropout: 0.10` is the clear working winner: it improves BCE, Brier, ROC-AUC and monotonicity simultaneously. Learning rate and explicit L2 show at most small, mixed gains and are not worth further independent sweeps.

**Working benchmark:** use `dropout_010.yaml` as the control for the final local optimization pass. Keep the canonical baseline config unchanged until this local pass is complete; that preserves the completed screen as an exact reproducibility record.

## Active experiment: local dropout and interaction follow-up

This is intentionally the final generic optimization pass before weather-specific architecture work.

The local sweep asks only two questions:

1. is the dropout optimum slightly below or above `0.10`?;
2. do the only mildly interesting LR/L2 settings add anything when combined with the dropout winner?

| Config | Learning rate | L2 penalty | Dropout | Role |
| --- | ---: | ---: | ---: | --- |
| `dropout_010.yaml` | 0.001 | 1e-9 | 0.10 | working control |
| `dropout_0075.yaml` | 0.001 | 1e-9 | 0.075 | local lower bracket |
| `dropout_0125.yaml` | 0.001 | 1e-9 | 0.125 | local upper bracket |
| `dropout_015.yaml` | 0.001 | 1e-9 | 0.15 | upper boundary check |
| `dropout_010_l2_1e-6.yaml` | 0.001 | 1e-6 | 0.10 | L2 interaction |
| `dropout_010_lr_2e-3.yaml` | 0.002 | 1e-9 | 0.10 | LR interaction |

Run from `ml/`:

```bash
export ML_DATABASE_URL='postgresql://...'

glideator-ml sweep xc \
  --configs \
    configs/xc/optimization/training/dropout_010.yaml \
    configs/xc/optimization/training/dropout_0075.yaml \
    configs/xc/optimization/training/dropout_0125.yaml \
    configs/xc/optimization/training/dropout_015.yaml \
    configs/xc/optimization/training/dropout_010_l2_1e-6.yaml \
    configs/xc/optimization/training/dropout_010_lr_2e-3.yaml \
  --output-dir outputs/xc/optimization/training/local-dropout
```

The sweep runner loads the XC dataset once, verifies benchmark/dataset/evaluation identity, isolates every artifact directory and writes `sweep_summary.json`.

### Selection rule

Use macro BCE and Brier as the primary tie-breakers, with ROC-AUC and monotonicity required not to show a meaningful regression. Also inspect per-threshold metrics for the harder XC50–XC100 targets, best epoch, validation loss, training time and parameter count.

Do not open another generic LR/L2/dropout grid after this. Pick the strongest local candidate. If it is materially better than `dropout_010.yaml`, confirm it on paired seeds 42–46. If the differences are negligible, keep `dropout: 0.10` without spending more runs.

After that, freeze the optimized conventional MLP benchmark and move directly to weather/profile-specific architectures.
