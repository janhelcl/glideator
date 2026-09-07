# XC GPU and architecture experiments

This note tracks the next phase after migrating the production XC model into the reproducible `glideator_ml.xc` pipeline.

## GPU batch-size decision

The RTX 3090 profile flattened quickly while using very little VRAM:

| Batch | Samples/s | Approx. epoch | CUDA allocated | Steps/epoch |
| ---: | ---: | ---: | ---: | ---: |
| 2,048 | 59,712 | 3.03 s | 0.09 GiB | 89 |
| 4,096 | 66,190 | 2.74 s | 0.12 GiB | 45 |
| 8,192 | 69,125 | 2.62 s | 0.17 GiB | 23 |
| 16,384 | 70,927 | 2.55 s | 0.28 GiB | 12 |
| 32,768 | 70,558 | 2.57 s | 0.49 GiB | 6 |
| 65,536 | 71,296 | 2.54 s | 0.92 GiB | 3 |

**Decision: use batch size 8,192 for architecture experiments.** It reaches at least 95% of peak measured throughput while preserving substantially more optimizer steps than the larger batches.

The profile suggests the current path is transfer-bound rather than compute- or memory-bound. That is not worth optimizing now: the entire fit epoch already takes about 2.6 seconds, so architecture iteration has much higher expected value than shaving more time off the input path.

The full profile is persisted in `outputs/xc/gpu-batch-profile/batch_profile.json` and logged to MLflow.

## Training-budget normalization

Changing from 2,048 to 8,192 reduces optimizer steps per epoch by roughly 4x. Keeping the old `patience: 10` would therefore also reduce the early-stopping patience in optimizer-step terms by roughly 4x.

For the first architecture sweep:

- batch size: `8192`;
- learning rate: `0.001`;
- max epochs: `200`;
- patience: `40` epochs;
- optimizer/objective/regularization otherwise unchanged.

At 23 steps per epoch, `patience: 40` is about 920 stale optimizer steps, close to the old 2,048-batch policy's 890 stale steps. This keeps the hardware change from silently becoming an under-training change.

## Benchmark

The warehouse currently ends on `2024-11-30`, so architecture experiments use the explicit benchmark ID `xc-temporal-2024-jan-nov-v1`:

- fit: before `2023-01-01`;
- validation/model selection: calendar year 2023;
- final evaluation: `2024-01-01` through `2024-11-30`;
- seed: `42`;
- same feature contract and scaler behavior for every run.

Do not mix these Jan-Nov results with a future full-calendar-2024 benchmark without rerunning the candidates.

## First architecture sweep

The configs live under `configs/xc/architecture/`. Each variant changes one structural hypothesis from the control.

| Config | Change from control | Question |
| --- | --- | --- |
| `control.yaml` | current `ExpandedGlideatorNet` | reproducible 8,192-batch control |
| `ordinal.yaml` | `prediction_head_type: ordinal` | do nested threshold semantics improve calibration and monotonicity? |
| `no_parallel.yaml` | remove parallel deep tower | does that tower add useful signal beyond CrossNet? |
| `no_cross.yaml` | `cross_layers: 0` | does explicit feature crossing add value? |
| `time_specific_cross.yaml` | `share_cross_net: false` | should 09/12/15 have separate interaction functions? |
| `wider_fusion.yaml` | main tower `[128, 64]` | is the final fusion bottleneck too narrow? |

Run the complete sweep on the GPU host:

```bash
cd ml
export ML_DATABASE_URL='postgresql://...'

for config in \
  control \
  ordinal \
  no_parallel \
  no_cross \
  time_specific_cross \
  wider_fusion
 do
  glideator-ml run xc --config "configs/xc/architecture/${config}.yaml"
 done
```

All runs go to the `glideator-xc` MLflow experiment with distinct `model_family` tags and unique artifact directories under `outputs/xc/architecture/`. ONNX export is disabled during exploration; export/parity belongs after architecture selection, not in every screening run.

The most interesting initial hypothesis remains the **ordinal head**. `XC0` through `XC100` are nested events, while the legacy multilabel head learns eleven independent probabilities and only nudges monotonicity with a tiny penalty. `OrdinalHead` enforces monotonic outputs by construction.

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

After this screen, tune width/depth/embedding size and optimization hyperparameters **around the winning family**, rather than starting with a large mixed architecture/hyperparameter grid.
