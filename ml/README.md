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

S2S experiments are evaluated on **first visits** only. The harness currently
defines two benchmark semantics.

### s2s-v1: held-out-pilot generalization

Pilots are deterministically split into train and evaluation groups. The model is
fitted only on train pilots. Every evaluation pilot contributes walk-forward
examples:

```text
[A]       -> B
[A, B]    -> C
[A, B, C] -> D
```

This prevents a held-out pilot's future visits from leaking into learned site
embeddings. The split identity and stochastic model training use separate seeds:

```yaml
data:
  split_strategy: pilot
  split_seed: 42

model:
  seed: 42

evaluation:
  benchmark_id: s2s-v1
```

Keep `data.split_seed` fixed when comparing model seeds or architectures. Change
only `model.seed` for repeated stochastic runs.

### s2s-v2: temporal production simulation

The temporal benchmark trains embeddings using only first visits known before a
fixed cutoff. Evaluation targets are first visits on or after that cutoff. For
each target, the pilot history contains only sites that pilot had discovered
before the target, including legitimate pre-cutoff history.

```yaml
data:
  split_strategy: temporal
  temporal_cutoff: "2024-01-01"

evaluation:
  benchmark_id: s2s-v2
```

The checked-in v2 benchmark uses 2024-01-01 as its fixed cutoff. Treat the cutoff
as part of the benchmark definition: changing it should also use a new
`benchmark_id`.

The runner logs the `benchmark_id`, split strategy, cutoff/seed, dataset
fingerprint, and an `eval_set_fingerprint` derived from the exact walk-forward
examples, so accidentally incomparable runs are visible in MLflow.

The harness supports truncated SVD and the contrastive architecture used by the
current production model. Item embeddings are normalized and exported using the
production-compatible keys `site_to_idx`, `idx_to_site`, and `matrix`. Extra
metadata is additive, so an artifact can replace the existing S2S pickle without
changing serving code.

## Setup

```bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install -e '.[contrastive,test,tracking]'
```

Point the experiment runner at the analytics database:

```bash
export ML_DATABASE_URL='postgresql://...'
```

By default MLflow logs to the SQLite database under `./mlruns`. A remote server
can be used with:

```bash
export MLFLOW_TRACKING_URI='http://localhost:5000'
```

Run the SVD v1 baseline:

```bash
glideator-ml run s2s --config configs/s2s/svd.yaml
```

Run the production-equivalent contrastive v1 benchmark:

```bash
glideator-ml run s2s --config configs/s2s/contrastive-prod-equivalent.yaml
```

Run the temporal v2 benchmark:

```bash
glideator-ml run s2s --config configs/s2s/contrastive-temporal-v2.yaml
```

For a fixed-split 5-seed v1 contrastive comparison, leave
`data.split_seed: 42` unchanged and run the same config with
`model.seed: 42`, `43`, `44`, `45`, and `46`. All five reports should
have identical `events`, `eval_pilots`, and `eval_set_fingerprint`.

For v2 seed comparisons, keep `temporal_cutoff` unchanged and vary only
`model.seed`.

The command writes a production-compatible pickle plus an evaluation report under
`outputs/`, and logs the config, dataset fingerprint, benchmark identity,
evaluation-set fingerprint, metrics, Git SHA, and artifacts to MLflow.

To inspect local runs:

```bash
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db
```

## Data contract

The database loader reads `fact_flights` and joins `dim_sites` by the XContest
site name to obtain `site_id`. The schema is configurable with `data.schema`
(`mart` by default; the production-equivalent configs use
`glideator_mart`). It reduces raw flights to one first-visit event per
pilot/site before any split or model fitting.

For isolated experiments and tests, the same runner can consume a CSV containing:

```text
pilot,site_id,date,start_time
```

## Evaluation

S2S reports the original ranking metrics unchanged:

- HitRate@k
- MRR@k
- NDCG@k
- catalog coverage@k
- average log popularity@k
- cold-start target rate
- known-source rate
- number of walk-forward events

It additionally reports:

- `end_to_end_hit_rate_at_k`, where every benchmark event is in the denominator,
  including cold-start and unservable events
- history-length slices: one previous site, two-to-three sites, and four-plus
- target-popularity slices: head, tail, and cold-start targets

The popularity head is the top 20% of training-catalog sites by first-visit
count; all other known sites are tail. Each slice includes event count, eligible
event count, conditional HitRate/MRR/NDCG, and end-to-end HitRate.

Task-specific evaluators deliberately live inside each model family rather than
being forced into one generic metric abstraction.
