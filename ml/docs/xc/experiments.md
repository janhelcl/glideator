# XC experiments

This note tracks the active XC experiment sequence after migrating the production model family into the reproducible `glideator_ml.xc` pipeline. Run-level metrics belong in MLflow; durable conclusions live in `docs/decisions/`.

## Fixed experiment policy

Architecture comparisons use:

- benchmark: `xc-temporal-2024-jan-nov-v1`;
- fit rows: before `2023-01-01`;
- validation/model selection: calendar year 2023;
- final evaluation: `2024-01-01` through `2024-11-30`;
- batch size: `8192`;
- learning rate: `0.001` unless an experiment explicitly targets it;
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

## Completed site-embedding screen

The seed-42 screen varied only site-embedding dimension:

| Embedding dim | Macro BCE ↓ | Macro Brier ↓ | Macro ROC-AUC ↑ | Mono rate ↓ | Best epoch | Parameters |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 0.16101 | 0.04866 | 0.93933 | 0.0123 | 117 | 36.4k |
| 16 | 0.15944 | 0.04828 | 0.93964 | 0.0286 | 84 | 40.4k |
| 32 | **0.15787** | **0.04788** | 0.94098 | 0.0270 | 45 | 48.5k |
| 64 | 0.15833 | 0.04790 | **0.94156** | 0.0205 | 42 | 64.7k |

**Decision:** keep `site_embedding_dim: 32` and close embedding-size tuning. See [ADR 0012](../decisions/0012-xc-keep-32d-site-embedding.md).

## Completed training and regularization optimization

The first seed-42 screen identified dropout as the only generic optimization axis with a clear joint gain:

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

A final local screen then checked the neighborhood around `dropout: 0.10` plus the only plausible LR/L2 interactions:

| Config | BCE ↓ | Brier ↓ | ROC-AUC ↑ | Mono rate ↓ | Best epoch |
| --- | ---: | ---: | ---: | ---: | ---: |
| `dropout_010` | **0.15686** | 0.04762 | **0.94206** | 0.0014 | 86 |
| `dropout_0075` | 0.15760 | 0.04771 | 0.94175 | 0.0016 | 86 |
| `dropout_0125` | 0.15748 | 0.04771 | 0.94176 | 0.0012 | 86 |
| `dropout_015` | 0.15701 | **0.04760** | 0.94198 | **0.0006** | 86 |
| `dropout_010_l2_1e-6` | 0.15769 | 0.04779 | 0.94191 | 0.0012 | 86 |
| `dropout_010_lr_2e-3` | **0.15641** | 0.04772 | 0.94112 | 0.0025 | 31 |

There is no material joint improvement over `dropout: 0.10`. Dropout 0.15 moves tiny amounts between metrics; extra L2 is worse; LR 0.002 buys BCE at the expense of Brier, ROC-AUC and monotonicity. Generic baseline tuning stops here.

**Decision:** freeze `configs/xc/baselines/conventional_mlp.yaml` at `dropout: 0.10` and use it as the canonical control for weather-specific work. See [ADR 0013](../decisions/0013-xc-freeze-optimized-conventional-benchmark.md).

## Frozen conventional benchmark

The canonical conventional model is now:

- no CrossNet (`cross_layers: 0`);
- raw per-time bypass retained;
- shared per-time MLP `[64, 32]`;
- fusion tower `[64, 32]`;
- site embedding dimension `32`;
- independent multilabel head;
- dropout `0.10`;
- batch size `8192` and learning rate `0.001`.

Seed-42 reference metrics are BCE `0.15686`, Brier `0.04762`, ROC-AUC `0.94206`, monotonic violation rate `0.0014`, best epoch `86`.

Do not reopen generic capacity, embedding, LR, L2 or dropout tuning while screening weather-specific representations.
