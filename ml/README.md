# Glideator ML

A small, model-family-agnostic experimentation workspace for Glideator.

The shared layer standardizes experiment execution, provenance, tracking, and reproducibility. Task semantics deliberately stay with the task: each model family owns its data preparation, benchmarks, evaluator, models, and artifact contract.

## Model families

| Task | Purpose | Status | Docs |
| --- | --- | --- | --- |
| S2S | Recommend new flying sites from a pilot's discovered-site history | Active | [docs/s2s/README.md](docs/s2s/README.md) |
| XC | Predict flight / XC potential | Planned migration | — |
| D2D | Retrieve analogous historical days | Planned migration | — |

## Layout

~~~
ml/
├── configs/                  Reproducible experiment configurations
├── glideator_ml/             Shared harness plus task implementations
│   └── <task>/               Task-owned data, models, evaluator, artifact
├── docs/
│   ├── <task>/               Task methodology and model catalogue
│   └── decisions/            Durable cross-model / benchmark decisions
├── tests/                    Synthetic and contract tests
└── outputs/                  Local artifacts and reports; ignored by git
~~~

The documentation follows the same ownership rule as the code:

- A **task README** defines the prediction problem, benchmark semantics, evaluation, and serving boundary.
- A **model page** explains one architecture: hypothesis, delta from the reference model, config, and serving implications.
- A **decision record** captures reasoning that should constrain future work: benchmark identity, artifact contracts, promotion rules, or shared training policy.
- **MLflow** is the source of truth for individual run metrics. Docs record durable conclusions, not copied leaderboards.

See [docs/decisions/README.md](docs/decisions/README.md) for the decision-record convention.

## Setup

~~~bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install -e '.[contrastive,test,tracking]'
~~~

Point the runner at the analytics database:

~~~bash
export ML_DATABASE_URL='postgresql://...'
~~~

MLflow defaults to the local SQLite store under mlruns/. A remote tracking server can be supplied with:

~~~bash
export MLFLOW_TRACKING_URI='http://localhost:5000'
~~~

## Running experiments

The CLI is intentionally thin:

~~~text
glideator-ml run <task> --config <config>
glideator-ml backfill <task> --config <config>
~~~

Task docs define the benchmark-specific configs and comparison rules. Start with [S2S](docs/s2s/README.md).

Every run should make it possible to answer:

1. What exact dataset and evaluation set did this use?
2. What benchmark definition did it claim to implement?
3. What code and configuration produced the artifact?
4. Is the artifact compatible with production serving?
5. Which stochastic seed changed, and which benchmark inputs stayed fixed?

The harness logs dataset fingerprints, evaluation-set fingerprints, benchmark identity, Git SHA, model metadata, metrics, and artifacts to MLflow.

## Promotion boundary

This workspace is for experimentation and comparison. Producing an artifact does **not** make it production-ready.

Promotion is explicit and should require:

- a benchmark result judged against the appropriate reference;
- reproducibility across the required seeds;
- a documented serving contract;
- compatibility with, or an intentional change to, production inference;
- a recorded decision when the change affects future experiments or serving.

Task docs call out whether a model is directly serving-compatible or needs serving changes.
