# XC forecast model

XC is Glideator's main forecast model family. It predicts the probability that the best flight from a site on a day exceeds each threshold from 0 through 100 points in 10-point increments.

## Prediction contract

For each site/date pair the production model consumes:

- weather features for 09:00, 12:00 and 15:00;
- static site features;
- a learned site-ID embedding;
- `weekend`, `year`, `day_of_year_sin` and `day_of_year_cos`.

It returns eleven probabilities named `XC0`, `XC10`, ..., `XC100`. Training targets use the strict rule `max_points > threshold`.

The current production architecture is `ExpandedGlideatorNet`: each weather time slice is combined with the site and date context, processed by a full-rank cross network, concatenated across the three times, and passed through a deep network and prediction head.

## Migration status

The first migration slice moves the stable model contract out of the legacy `net/` and notebook-oriented training area into `glideator_ml.xc`:

- `model.py` contains the production architecture and fixed scaling layer;
- the TorchRec `CrossNet` is replaced by a small pure-PyTorch implementation with the same equation, parameter names and parameter shapes;
- `preprocessing.py` owns target thresholds, date features and the production weather-column split;
- `objective.py` owns the summed per-threshold BCE objective and adjacent-threshold monotonicity penalty;
- contract tests lock the migrated behavior.

This is intentionally a compatibility migration, not a model change.

## Serving boundary

Production serving has **not** moved. The backend still loads its existing ONNX artifact and scores it through the legacy `net.io.score_onnx` path.

The migrated architecture is designed to accept legacy **state dicts** without requiring TorchRec. A legacy full-object PyTorch pickle still depends on the old Python module path and dependency environment; it is not the promotion format for the new workspace.

No new XC artifact should be promoted until a parity run demonstrates that the migrated model, given the same weights and inputs, matches the current production artifact within an explicit tolerance.

## What remains

The remaining XC migration should proceed in this order:

1. define a deterministic XC dataset and benchmark identity;
2. migrate data extraction, splitting and scaler fitting out of notebooks;
3. add config-driven training and MLflow tracking;
4. reproduce the current model from the migrated pipeline and compare it with the production reference;
5. move ONNX export into the XC task and add PyTorch-to-ONNX parity tests;
6. define the production artifact contract and promotion gate;
7. switch backend serving only after the gate is satisfied.

The train/evaluation split and benchmark identity are deliberately not being inferred from the old notebooks during this first slice. They should be made explicit before experiment results from the migrated XC pipeline are treated as comparable.

## Legacy sources

Until the migration is complete, the reference behavior lives in:

- `net/net/net.py` — architecture;
- `net/net/preprocessing.py` — target and date feature semantics;
- `net/net/export.py` and `net/net/io.py` — ONNX input/output contract;
- `analytics/training/training.py` — training objective and loop;
- `analytics/training/` notebooks — current data preparation and experiment workflow.
