# XC forecast model

XC is Glideator's main forecast model family. It predicts the probability that the best flight from a site on a day exceeds each threshold from 0 through 100 points in 10-point increments.

## Prediction contract

For each site/date pair the model consumes:

- weather features for 09:00, 12:00 and 15:00;
- static site features;
- a learned site-ID embedding;
- `weekend`, `year`, `day_of_year_sin` and `day_of_year_cos`.

It returns eleven probabilities named `XC0`, `XC10`, ..., `XC100`. Training targets use the strict rule `max_points > threshold`.

The production architecture is `ExpandedGlideatorNet`: each weather time slice is combined with site/date context, processed through a shared full-rank cross network and a shared parallel deep tower, concatenated across the three times, and passed through the main deep tower and prediction head.

## Migrated pipeline

XC now has an executable experiment path under `glideator_ml.xc`:

- `model.py` — production architecture and fixed scaling layers;
- `preprocessing.py` — target/date semantics and weather-time contract;
- `objective.py` — legacy summed BCE and monotonicity penalty;
- `benchmark.py` — temporal benchmark, feature contract and fingerprints;
- `selection.py` — internal temporal model-selection split;
- `data.py` — database/CSV extraction, validation and scaler fitting;
- `training.py` — seeded config-driven PyTorch training with early stopping;
- `evaluation.py` — BCE, Brier, ROC-AUC and monotonicity diagnostics;
- `onnx.py` — production-shaped ONNX export, scoring and numerical parity;
- `compatibility.py` — reconstructs the migrated PyTorch architecture and exact weights directly from the served ONNX graph;
- `reference.py` — evaluation of an existing ONNX artifact on the fixed benchmark;
- `promotion.py` — candidate/reference comparability and promotion eligibility;
- `workflow.py` — single-snapshot reference → candidate → promotion orchestration;
- `run.py` — report/checkpoint creation and MLflow tracking/backfill.

TorchRec is no longer required. The replacement full-rank `CrossNet` keeps the legacy equation, parameter names and state-dict shapes so production weights can be represented by the migrated model.

## Benchmark: `xc-temporal-2024-v1`

The stable XC benchmark deliberately replaces the old nondeterministic `is_validation` flag:

- data starts at `2021-01-01`;
- site domain is capped at the existing production range, `site_id <= 250`;
- development window ends `2023-12-31`;
- final evaluation is the full 2024 calendar year;
- evaluation sites must already exist in development data;
- the configured evaluation boundaries must actually exist after incomplete rows are removed;
- source values, feature order and exact evaluation rows receive SHA-256 fingerprints.

Model selection is also temporal. The production-reference config uses rows before `2023-01-01` for fitting and 2023 for early stopping. The 2024 benchmark is never consulted during training or model selection.

This benchmark is defined in [decision 0005](../decisions/0005-xc-temporal-benchmark.md). Results from the old random 80/20 per-site split are not directly comparable.

Scaler fitting preserves one non-obvious legacy behavior: weather mean/std are fitted from the **12:00 slice only** and the same scaler is applied to 09:00, 12:00 and 15:00. Site scaling uses fit rows only.

## Production architecture contract

The structural model configuration is no longer inferred from notebook examples. It is read and tested directly from the initializers embedded in the currently served `backend/app/models/model.onnx`:

- 77 weather features per time slice;
- three static site features and four date features;
- 251 embedding slots for site IDs 0–250;
- 32-dimensional site embedding;
- 116 inputs per time slice;
- two shared full-rank CrossNet layers;
- shared parallel deep tower `[128, 64, 32]`;
- the 116-dimensional cross output and 32-dimensional parallel output form 148 values per time slice;
- three time slices form 444 values for the main deep tower;
- main deep tower `[64, 32]`;
- eleven independent multilabel probability heads.

`compatibility.py` derives that constructor contract from ONNX parameter names/shapes, rebuilds `ExpandedGlideatorNet`, and loads the exact served weights into the TorchRec-free implementation. CI compares that reconstructed PyTorch model against ONNX Runtime on identical production-shaped inputs. This is the migration proof for model structure and forward semantics; it is independent of retraining.

The served artifact also has direct repository provenance. Before the ONNX-serving switch it existed as `backend/app/models/model.pth`; the production model was updated in commit `15eb413` (`model on fixed dataset`) and later moved to ONNX serving in commit `7988d05`.

Historical **training** choices such as the optimizer trajectory, stochastic seed, and exact stopping epoch are not encoded in the served graph. The migrated training config therefore treats those as experiment policy rather than claiming they can be recovered from ONNX.

## Candidate reference config

`configs/xc_production_reference.yaml` uses the graph-confirmed production structure:

- 251 embedding slots and 32-dimensional embedding;
- two shared full-rank cross layers;
- shared parallel tower `[128, 64, 32]`;
- main deep tower `[64, 32]`;
- independent multilabel probability heads;
- explicit migrated training/regularization policy.

Run the candidate alone with:

~~~bash
cd ml
export ML_DATABASE_URL='postgresql://...'
glideator-ml run xc --config configs/xc_production_reference.yaml
~~~

A run writes:

- `xc_checkpoint.pt` — state dict, architecture config, fitted scalers, feature contract and provenance;
- `training_history.json` — epoch-level fit/validation losses and learning rate;
- `evaluation.json` — benchmark identity, fingerprints, model metadata and final 2024 metrics;
- `model.onnx` — production-shaped exported artifact;
- ONNX parity metrics measured against the PyTorch model;
- the same parameters, metrics, tags and artifacts to MLflow when tracking is enabled.

The checkpoint and ONNX are experiment artifacts until the promotion gate passes and an explicit serving change is made.

## Served production reference

The currently deployed `backend/app/models/model.onnx` can be scored on exactly the same 2024 benchmark:

~~~bash
glideator-ml evaluate xc --config configs/xc_served_reference.yaml
~~~

That run records the same dataset/evaluation fingerprints and feature contract plus the SHA-256 fingerprint of the served ONNX file. Its report is written to `outputs/xc/served-reference/evaluation.json` and can also be logged to MLflow.

## Promotion gate

After both reports exist, compare them with:

~~~bash
glideator-ml compare xc --config configs/xc_production_reference.yaml
~~~

The comparator first requires exact equality of:

- benchmark ID;
- full dataset fingerprint;
- evaluation-set fingerprint;
- feature contract.

It then requires successful candidate PyTorch ↔ ONNX parity and applies the explicit rules under `promotion.rules`. The initial compatibility policy allows no regression in macro BCE, macro Brier score, or macro ROC-AUC versus the served artifact.

The result is written to `outputs/xc/production-reference/promotion.json`. A non-eligible candidate makes the CLI exit non-zero. Passing means **eligible for an explicit serving change**, not automatically deployed.

For the real migration run, prefer the combined workflow:

~~~bash
glideator-ml benchmark xc \
  --config configs/xc_production_reference.yaml \
  --reference-config configs/xc_served_reference.yaml
~~~

This validates that both configs describe the same data query and benchmark, loads and prepares the analytics dataset **once**, evaluates the served reference and trains/evaluates the candidate against that same in-memory snapshot, then applies the promotion policy. Candidate and reference therefore cannot drift because the warehouse changed between reads; fingerprints remain part of the persisted comparison contract and provenance.

See [decision 0006](../decisions/0006-xc-promotion-gate.md).

## Evaluation metrics

Both candidate and served-reference runners report:

- summed per-threshold BCE as `validation_loss`;
- macro and per-threshold BCE;
- macro and per-threshold Brier score;
- ROC-AUC for thresholds with both classes present;
- macro ROC-AUC across valid thresholds;
- fraction and average magnitude of adjacent-threshold monotonicity violations.

Candidate runs additionally record fit/validation row counts, best epoch, best internal validation loss, and ONNX parity diagnostics.

## Serving boundary

Production serving has **not** moved. The backend still loads `backend/app/models/model.onnx` and scores it through `net.io.score_onnx`.

The migrated architecture can reconstruct the current production state directly from ONNX without TorchRec. Legacy full-object PyTorch pickles remain tied to the old module path and are not the promotion format.

## What remains

The remaining migration steps are operational:

1. run the combined `benchmark xc` workflow against the real analytics database and record both runs in MLflow;
2. inspect `promotion.json`; tune/reproduce the candidate if the strict migration gate fails;
3. switch the backend artifact only after the gate passes;
4. retire the notebook/`net/` training path after production cutover.

The Render production database is not the analytics source: it retains the historical 231-value weather vectors used by D2D, but not the daily `max_points` labels required by this benchmark. The real benchmark therefore still needs the analytics/training database exposed through `ML_DATABASE_URL`.

## Legacy sources

Until cutover, historical behavior still lives in:

- `net/net/net.py` — architecture implementation;
- `net/net/preprocessing.py` — target/date semantics;
- `net/net/export.py` and `net/net/io.py` — historical ONNX input/output contract;
- `analytics/training/training.py` — historical training objective/loop;
- `analytics/training/data_prep/crate_fs_table.ipynb` — legacy feature-store build and random validation flag;
- `analytics/training/fit_scalers.ipynb` — legacy scaler semantics.
