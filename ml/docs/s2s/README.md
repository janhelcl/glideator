# S2S — Site-to-site discovery

S2S recommends **new sites a pilot has not yet visited** from the set of sites they have already discovered.

This is a discovery recommender, not a next-flight predictor. Training and evaluation therefore operate on each pilot's **first visit** to each site.

## Prediction problem

A pilot's ordered first visits:

~~~text
A, B, C, D
~~~

produce walk-forward examples such as:

~~~text
[A]       -> B
[A, B]    -> C
[A, B, C] -> D
~~~

The target is always a newly discovered site. Previously visited sites are excluded from recommendations.

## Data contract

The database loader reads fact_flights and joins dim_sites by the XContest site name to obtain site_id. The schema is configurable through data.schema; production-equivalent configs use glideator_mart.

Raw flights are reduced to one first-visit event per pilot/site **before** splitting or fitting.

For isolated tests the same runner can consume CSV data with:

~~~text
pilot,site_id,date,start_time
~~~

## Benchmarks

### s2s-v1 — held-out-pilot generalization

Pilots are deterministically split into train and evaluation groups. The model is fitted only on train pilots; evaluation pilots contribute walk-forward first-visit examples.

This answers: **does the model generalize to pilots it never trained on?**

Benchmark identity and model randomness are intentionally separate:

~~~yaml
data:
  split_strategy: pilot
  split_seed: 42

model:
  seed: 42

evaluation:
  benchmark_id: s2s-v1
~~~

When comparing architectures or stochastic seeds, keep data.split_seed fixed. Vary model.seed only.

### s2s-v2 — temporal production simulation

The temporal benchmark trains on first visits before a fixed cutoff and evaluates first visits on or after that cutoff. A target's history may include legitimate discoveries made before the cutoff.

~~~yaml
data:
  split_strategy: temporal
  temporal_cutoff: "2024-01-01"

evaluation:
  benchmark_id: s2s-v2
~~~

The checked-in v2 benchmark uses 2024-01-01. The cutoff is part of the benchmark definition; changing it requires a new benchmark identity.

The runner logs benchmark_id, split strategy, split seed or cutoff, dataset fingerprint, and an eval_set_fingerprint derived from the exact walk-forward events.

See [ADR 0001](../decisions/0001-stable-benchmark-identity.md).

## Evaluation

The core ranking metrics are:

- HitRate@k
- MRR@k
- NDCG@k
- catalog coverage@k
- average log popularity@k
- cold-start target rate
- known-source rate
- number of walk-forward events

The evaluator also reports:

- end_to_end_hit_rate_at_k, using every benchmark event as the denominator;
- history slices: 1 site, 2–3 sites, and 4+ sites;
- target popularity slices: head, tail, and cold-start.

The popularity head is the top 20% of the training catalogue by first-visit count. Every other known site is tail.

Task-specific evaluation deliberately lives in glideator_ml/s2s/evaluation.py rather than in a generic metric abstraction. See [ADR 0002](../decisions/0002-task-owned-semantics.md).

## Model catalogue

| Model | Role / hypothesis | Serving today | Doc |
| --- | --- | --- | --- |
| SVD | Classical latent-factor baseline | Compatible | [SVD](models/svd.md) |
| Contrastive additive | Production-equivalent neural reference | Compatible | [Contrastive](models/contrastive.md) |
| DeepSets | Nonlinear set encoder after pooling | Requires scorer-aware serving | [DeepSets](models/deepsets.md) |
| Asymmetric additive | Untie history and candidate embeddings | Requires scorer-aware serving | [Asymmetric](models/asymmetric.md) |
| Transformed additive | Nonlinear per-site transform while preserving additive history | Requires scorer-aware serving | [Transformed additive](models/transformed-additive.md) |
| Candidate attention | Candidate-specific residual correction over additive history | Requires scorer-aware serving | [Candidate attention](models/candidate-attention.md) |

The model pages intentionally do not duplicate current metric tables. Run metrics and artifacts belong in MLflow; model docs explain architecture and experimental intent. Durable promote/reject decisions should be recorded under docs/decisions/.

## Checked-in configs

~~~text
configs/s2s/svd.yaml
configs/s2s/contrastive-prod-equivalent.yaml
configs/s2s/contrastive-temporal-v2.yaml
configs/s2s/deepsets.yaml
configs/s2s/asymmetric.yaml
configs/s2s/transformed-additive.yaml
configs/s2s/candidate-attention.yaml
~~~

Run a model from the ml/ directory:

~~~bash
glideator-ml run s2s --config configs/s2s/contrastive-prod-equivalent.yaml
~~~

For fixed-split seed comparisons, leave data.split_seed unchanged and vary only model.seed. All comparable runs should have identical event counts and eval_set_fingerprint.

For temporal comparisons, keep temporal_cutoff unchanged and vary only model.seed.

## Artifacts and serving

All S2S artifacts preserve the legacy payload keys:

~~~text
site_to_idx
idx_to_site
matrix
~~~

SVD and contrastive additive can be served using the current backend contract.

Models with learned history/candidate scoring state add an optional scorer payload. Their evaluator uses that scorer so experiment-time inference matches training, but they must not be promoted until production serving understands the scorer.

See [ADR 0003](../decisions/0003-scorer-aware-artifacts.md).

## Tracking and recovery

A successful run writes the model artifact and evaluation.json under outputs/ and logs configuration, fingerprints, benchmark identity, metrics, Git SHA, and artifacts to MLflow.

If training and evaluation succeed but MLflow is temporarily unavailable, the saved run can be backfilled without retraining:

~~~bash
glideator-ml backfill s2s --config configs/s2s/deepsets.yaml
~~~

Backfill is idempotent after mlflow_run_id has been persisted to evaluation.json.

Inspect local runs with:

~~~bash
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db
~~~
