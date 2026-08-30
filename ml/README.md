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

The harness supports truncated SVD, the contrastive architecture used by the
current production model, a DeepSets history encoder, an asymmetric additive
model, a transformed-additive model, and a residual candidate-attention model.
SVD and contrastive artifacts remain directly
production-compatible: item embeddings are normalized and exported using the
keys `site_to_idx`, `idx_to_site`, and `matrix`.

DeepSets learns a nonlinear permutation-invariant history encoder
`rho(pool(phi(site)))`. Its artifact preserves the same three legacy keys and
adds a small optional `scorer` payload containing the learned history-encoder
weights. The experiment evaluator uses that scorer so inference matches training.
The asymmetric model keeps additive history composition but learns separate
source and target site embeddings. Its target embeddings remain in `matrix`,
while the source embedding table is stored in the optional `scorer` payload.
The transformed-additive model applies the same DeepSets-style `phi -> rho`
nonlinear mapping independently to each history site, then sums those transformed
vectors before normalization. With a one-site history this has the same functional
form as DeepSets; for longer histories it preserves additive composition instead
of applying `rho` after pooling. Do not promote DeepSets, asymmetric, or
transformed-additive artifacts to the current backend until serving understands
their scorer payloads.

Candidate attention keeps the normalized summed-history query as a residual base,
then computes a separate single-head attention correction for each candidate site.
Q/K/V projections are learned, the attention scale is learned from a small 0.1
initial value, and the full catalog can be scored directly because S2S has only a
few hundred sites. Its artifact stores the raw history embedding table plus the
attention weights in `scorer`, so it also requires scorer-aware serving.

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

Run the DeepSets v1 benchmark on the same held-out-pilot split:

```bash
glideator-ml run s2s --config configs/s2s/deepsets.yaml
```

Run the asymmetric additive v1 benchmark:

```bash
glideator-ml run s2s --config configs/s2s/asymmetric.yaml
```

Run the transformed-additive v1 benchmark:

```bash
glideator-ml run s2s --config configs/s2s/transformed-additive.yaml
```

Run the residual candidate-attention v1 benchmark:

```bash
glideator-ml run s2s --config configs/s2s/candidate-attention.yaml
```

This model keeps the strong additive contrastive history representation and learns
only a candidate-specific correction. For each candidate, one attention head
weights the visited sites differently; the resulting context is added to the
normalized additive base before cosine scoring.

This ablation keeps the DeepSets `phi` and `rho` dimensions and all contrastive
training hyperparameters, but changes composition from
`rho(mean(phi(site)))` to `sum(rho(phi(site)))`. It is intended to isolate
whether the nonlinear per-site mapping is useful while post-pooling compression is
harmful.

The asymmetric config matches the production-equivalent contrastive hyperparameters
and benchmark. The sole architectural change is untied source and target embedding
tables; history is still summed and normalized before candidate scoring.

The checked-in DeepSets config keeps the contrastive optimizer, negative sampling,
embedding dimension, and benchmark identity aligned with the production-equivalent
contrastive config. Its new degrees of freedom are the per-site `phi` MLP, the
post-pooling `rho` MLP, and mean pooling over the already-discovered site set.

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

The command writes an S2S artifact plus an evaluation report under `outputs/`,
and logs the config, dataset fingerprint, benchmark identity, evaluation-set
fingerprint, metrics, Git SHA, and artifacts to MLflow. SVD and contrastive
artifacts are directly production-compatible; DeepSets, asymmetric,
transformed-additive, and candidate-attention artifacts require scorer-aware
serving.

If training and evaluation finish but MLflow is temporarily unavailable, restore
the configured tracking service and backfill the saved run without retraining:

```bash
glideator-ml backfill s2s --config configs/s2s/deepsets.yaml
```

Backfill is idempotent after the resulting `mlflow_run_id` has been saved to the
local evaluation report.

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
