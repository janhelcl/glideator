# Jev 1.13 hosted challenger

## Hypothesis

[Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) is a hosted probabilistic decision model rather than a trainable tabular or neural architecture. It accepts shared state plus typed questions and returns calibrated decision probabilities. The XC experiment asks whether that interface can produce useful held-out `P(XC > threshold)` forecasts without fitting model weights.

This is deliberately a challenger experiment, not a production-serving proposal. Jev cannot be fine-tuned on Glideator data, exported to ONNX, or served within the current low-resource backend.

## Frozen experiment contract

The executable config is `configs/xc/baselines/jev_1_13.yaml`.

- model: pinned `jev-1.13.0`, never the moving `jev-latest` alias;
- benchmark: `xc-temporal-2024-jan-nov-v1`;
- prior-fit rows: before `2023-01-01`;
- 2023: excluded from both historical priors and the final evaluation;
- final evaluation: `2024-01-01` through `2024-11-30`;
- outputs: eleven independent Noul probabilities for the existing strict targets `XC0` through `XC100`;
- evaluator: the same BCE, Brier, ROC-AUC and monotonicity diagnostics used by every XC candidate.

No evaluation label, `max_points`, or derived target enters a Jev request.

## Why the state is semantic

TypeSafe documents numeric precision and large irrelevant states as weaknesses of Jev 1.13. Sending the raw 231-value GFS vector would therefore test a known failure mode more than the model's decision interface.

The runner performs deterministic meteorological arithmetic in code and sends compact semantic evidence for 09:00, 12:00 and 15:00:

- surface and flying-layer wind categories, directions, speed and gust;
- lapse-rate stability category;
- temperature;
- estimated cloud-base category;
- low/mid-level humidity and precipitable-water categories;
- site location/elevation and calendar context.

Each threshold question also receives smoothed same-site/same-month, same-site and global occurrence frequencies computed only from the pre-2023 fit rows. Category labels are primary; rounded values remain supporting context.

This makes the tested system **Jev plus a fixed, non-leaky semantic adapter and historical priors**. It is not a claim that raw Jev is a weather model.

## Running

Install the hosted-model extra and set both data credentials:

~~~bash
cd ml
pip install -e '.[jev,tracking]'
export ML_DATABASE_URL='postgresql://...'
export TYPESAFE_API_KEY='...'
~~~

Start with a deterministic 100-row smoke run spread across the evaluation window:

~~~bash
glideator-ml benchmark-jev xc \
  --config configs/xc/baselines/jev_1_13.yaml \
  --limit 100
~~~

This writes `evaluation.partial.json` plus an append-only `predictions.jsonl`. Inspect token cost, latency and response quality, then continue the same cache into the full run:

~~~bash
glideator-ml benchmark-jev xc \
  --config configs/xc/baselines/jev_1_13.yaml
~~~

Every successful response is persisted immediately. Re-running skips completed site/date rows and retries missing ones. A cache manifest binds responses to the exact dataset, evaluation set, fit context, model version, prompt version and feature contract; a mismatched run is refused instead of silently mixing predictions.

Partial runs are not logged to MLflow. A full run is logged only when every evaluation row has a valid response. The report includes API model/version, token usage, estimated input cost, request latency and the normal XC metrics.

## Interpretation

Compare the completed run with the frozen conventional benchmark, whose seed-42 reference is BCE `0.15686`, Brier `0.04762`, ROC-AUC `0.94206`, and monotonic violation rate `0.0014`.

The first decision is whether Jev contains enough discriminative and calibration signal to justify further prompt/representation work. Do not tune against 2024. If iteration is justified, use 2023 as prompt-development data, version the prompt/state contract, and retain 2024 as the untouched final benchmark.

Even a metric win would not make this serving-compatible. A promotion proposal would also need to justify external availability, latency, privacy/data-retention, cost, version stability and the loss of offline inference.
