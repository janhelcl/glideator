# XC forecast model

XC is Glideator's main forecast model family. It predicts the probability that the best flight from a site on a day exceeds each threshold from 0 through 100 points in 10-point increments.

## Prediction contract

For each site/date pair the model consumes:

- weather features for 09:00, 12:00 and 15:00;
- static site features;
- a learned site-ID embedding;
- `weekend`, `year`, `day_of_year_sin` and `day_of_year_cos`.

It returns eleven probabilities named `XC0`, `XC10`, ..., `XC100`. Training targets use the strict rule `max_points > threshold`.

The production architecture is `ExpandedGlideatorNet`: each weather time slice is combined with site/date context, processed by a full-rank cross network, concatenated across the three times, and passed through a deep network and prediction head.

## Migrated pipeline

XC now has an executable experiment path under `glideator_ml.xc`:

- `model.py` — production architecture and fixed scaling layers;
- `preprocessing.py` — target/date semantics and weather-time contract;
- `objective.py` — legacy summed BCE and monotonicity penalty;
- `benchmark.py` — temporal split, feature contract and fingerprints;
- `data.py` — database/CSV extraction, validation and scaler fitting;
- `training.py` — seeded config-driven PyTorch training with early stopping;
- `evaluation.py` — BCE, Brier, ROC-AUC and monotonicity diagnostics;
- `run.py` — report/checkpoint creation and MLflow tracking/backfill.

TorchRec is no longer required. The replacement full-rank `CrossNet` keeps the legacy equation, parameter names and state-dict shapes so old state dicts remain loadable.

## Benchmark: `xc-temporal-2024-v1`

The first stable XC benchmark deliberately replaces the old nondeterministic `is_validation` flag:

- data starts at `2021-01-01`;
- site domain is capped at the existing production range, `site_id <= 250`;
- train window ends `2023-12-31`;
- evaluation is the full 2024 calendar year;
- evaluation sites must already exist in training;
- source values, feature order and exact evaluation rows receive SHA-256 fingerprints.

This benchmark is defined in [decision 0005](../decisions/0005-xc-temporal-benchmark.md). Results from the old random 80/20 per-site split are not directly comparable.

Scaler fitting also preserves one non-obvious legacy behavior: weather mean/std are fitted from the **12:00 slice only** and the same scaler is applied to 09:00, 12:00 and 15:00. Site scaling uses training rows only.

## Production-reference config

`configs/xc_production_reference.yaml` captures the historical production-sized architecture:

- 251 embedding slots for site IDs 0–250;
- 32-dimensional site embedding;
- two full-rank cross layers;
- deep layers `[128, 64, 32]`;
- independent multilabel probability heads;
- legacy-scale training defaults and regularization.

Run it with:

~~~bash
cd ml
export ML_DATABASE_URL='postgresql://...'
glideator-ml run xc --config configs/xc_production_reference.yaml
~~~

A run writes:

- `xc_checkpoint.pt` — state dict, architecture config, fitted scalers, feature contract and provenance;
- `training_history.json` — epoch-level train/validation losses and learning rate;
- `evaluation.json` — benchmark identity, fingerprints, model metadata and metrics;
- the same parameters, metrics, tags and artifacts to MLflow when tracking is enabled.

The checkpoint is an **experiment artifact**, not yet a production serving artifact.

## Evaluation

The runner reports the legacy summed per-threshold BCE as `validation_loss`, plus:

- macro and per-threshold BCE;
- macro and per-threshold Brier score;
- ROC-AUC for thresholds with both classes present;
- macro ROC-AUC across valid thresholds;
- fraction and average magnitude of adjacent-threshold monotonicity violations.

Row/site counts, best epoch and best validation loss are logged alongside the quality metrics.

## Serving boundary

Production serving has **not** moved. The backend still loads `backend/app/models/model.onnx` and scores it through `net.io.score_onnx`.

The migrated architecture accepts legacy **state dicts** without TorchRec. Legacy full-object PyTorch pickles still depend on the old module path and are not a promotion format.

No new XC checkpoint should be promoted until a parity run demonstrates that the migrated model, given the same weights and inputs, matches the currently served ONNX model within an explicit tolerance.

## What remains

The next migration steps are:

1. run `xc_production_reference.yaml` against the real analytics database and record the first benchmark run in MLflow;
2. validate the historical architecture/hyperparameters against the served artifact and any retained training checkpoint;
3. add ONNX export inside the XC task;
4. add PyTorch ↔ ONNX parity tests on representative real rows;
5. define promotion tolerances and the production artifact contract;
6. switch backend serving only after the parity gate is satisfied;
7. retire the notebook/`net/` training path after production cutover.

## Legacy sources

Until cutover, reference behavior still lives in:

- `net/net/net.py` — architecture;
- `net/net/preprocessing.py` — target/date semantics;
- `net/net/export.py` and `net/net/io.py` — ONNX input/output contract;
- `analytics/training/training.py` — training objective/loop;
- `analytics/training/data_prep/crate_fs_table.ipynb` — legacy feature-store build and random validation flag;
- `analytics/training/fit_scalers.ipynb` — legacy scaler semantics.
