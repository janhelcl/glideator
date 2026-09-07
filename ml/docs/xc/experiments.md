# XC GPU and architecture experiments

This note tracks the next phase after migrating the production XC model into the reproducible `glideator_ml.xc` pipeline.

## 1. Pick the GPU batch-size operating point

The original XC training workflow was CPU-oriented. The migrated reference config currently uses `batch_size: 2048`, but that value was not chosen for the RTX 3090.

Profile the real training step on the GPU host:

```bash
cd ml
export ML_DATABASE_URL='postgresql://...'
glideator-ml profile-batch xc \
  --config configs/xc_production_reference.yaml \
  --batch-sizes 2048 4096 8192 16384 32768 65536
```

The profiler:

- loads the normal XC dataset and uses the pre-2023 fit split;
- reconstructs the current architecture and objective;
- runs warm-up plus measured forward/backward/Adam steps;
- measures samples/second, mean step time and CUDA peak memory;
- reports the number of optimizer steps per epoch for each batch size;
- records the full result in `outputs/xc/production-reference/batch_profile.json`;
- recommends the **smallest** batch size reaching 95% of maximum measured throughput.

The distinction between `best_throughput_batch_size` and `recommended_batch_size` is deliberate. Very large batches can save little wall-clock time after GPU saturation while sharply reducing the number of optimizer updates. The architecture experiments should use the throughput knee rather than automatically using the largest batch that fits.

If the throughput curve is still rising steeply at 65,536, extend the sweep. If throughput saturates early while CUDA memory remains low, profile the input/transfer path before increasing batch size further.

## 2. Freeze training policy before architecture comparisons

Once the batch operating point is selected, keep the following fixed for the first architecture sweep:

- temporal fit/validation/evaluation windows;
- seed;
- optimizer and learning-rate policy;
- batch size;
- early-stopping policy;
- feature contract and scalers;
- objective and evaluation metrics.

Changing architecture and optimization policy simultaneously would make attribution difficult.

For a materially larger batch than 2,048, verify that the chosen learning rate still produces a sensible number of useful updates before starting the architecture sweep. Hardware throughput and optimization quality are separate questions.

## 3. First architecture sweep

Use the migrated production-shaped model as the control, but do not treat preserving its architecture as a goal. The first sweep should answer structural questions one at a time.

| Experiment | Change from control | Question |
| --- | --- | --- |
| control | current `ExpandedGlideatorNet` | reproducible comparison point |
| ordinal head | `prediction_head_type: ordinal` | does encoding the ordered XC thresholds directly improve calibration / monotonicity? |
| no parallel tower | remove `parallel_deep_hidden_units` | is the parallel MLP contributing useful signal beyond CrossNet? |
| no cross interaction | `cross_layers: 0` | is explicit feature crossing useful at all? |
| time-specific cross | `share_cross_net: false` | do 09/12/15 weather slices benefit from different interaction functions? |
| wider main tower | e.g. `[128, 64]` | is the final fusion bottleneck too narrow? |

Run these as separate MLflow experiments/configs with the same benchmark and training policy. Prefer one structural change per run for the first pass.

The most interesting hypothesis is the **ordinal head**: XC0...XC100 are nested events, while the legacy multilabel head learns eleven largely independent probabilities and only nudges monotonicity through a tiny penalty. `OrdinalHead` already enforces monotonic outputs by construction, so it is a clean first architecture experiment.

## 4. Selection metrics

Do not select architecture on ROC-AUC alone. Compare at minimum:

- macro BCE;
- macro Brier score;
- macro ROC-AUC;
- per-threshold BCE/Brier/AUC;
- monotonicity violations;
- parameter count and training time.

For architectures that are close on aggregate metrics, prefer the simpler model unless a meaningful threshold region improves consistently.

After the first sweep identifies a promising structure, tune width/depth/embedding size and optimization hyperparameters around that structure rather than running a large mixed grid immediately.
