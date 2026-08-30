# Glideator ML

A small, model-family-agnostic experimentation harness for Glideator.

The goal is not to make every model look the same. It is to make every experiment
reproducible, comparable, and promotable while each task owns its own data,
metrics, models, and artifact contract.

## Model families

- `s2s`: site discovery recommender. First complete implementation.
- `xc`: flight-potential model. Planned next.
- `d2d`: analogous-day retrieval. Planned next.

## S2S methodology

S2S experiments are evaluated on **first visits** only. Pilots are deterministically
split into train and evaluation groups. The model is fitted only on train pilots.
Every evaluation pilot then contributes walk-forward examples:

```text
[A]       -> B
[A, B]    -> C
[A, B, C] -> D
```

This prevents a held-out pilot's future visits from leaking into learned site
embeddings.

The first model is truncated SVD over the binary pilot-site matrix. Its item
embeddings are normalized and exported using the production-compatible keys
`site_to_idx`, `idx_to_site`, and `matrix`. Extra metadata is additive, so the
artifact can later replace the existing S2S pickle without changing serving code.

## Setup

```bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test,tracking]'
```

Point the experiment runner at the analytics database:

```bash
export ML_DATABASE_URL='postgresql://...'
```

By default MLflow logs to `./mlruns`. A remote server can be used with:

```bash
export MLFLOW_TRACKING_URI='http://localhost:5000'
```

Run the baseline:

```bash
glideator-ml run s2s --config configs/s2s/svd.yaml
```

The command writes a production-compatible pickle plus an evaluation report under
`outputs/`, and logs the config, dataset fingerprint, metrics, Git SHA, and
artifacts to MLflow.

To inspect local runs:

```bash
mlflow ui --backend-store-uri ./mlruns
```

## Data contract

The database loader reads `mart.fact_flights` and joins `mart.dim_sites` by the
XContest site name to obtain `site_id`. It reduces raw flights to one first-visit
event per pilot/site before any split or model fitting.

For isolated experiments and tests, the same runner can consume a CSV containing:

```text
pilot,site_id,date,start_time
```

## Evaluation

S2S currently reports:

- HitRate@k
- MRR@k
- NDCG@k
- catalog coverage@k
- average log popularity@k
- cold-start target rate
- known-source rate
- number of walk-forward events

Task-specific evaluators deliberately live inside each model family rather than
being forced into one generic metric abstraction.
