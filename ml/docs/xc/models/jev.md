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

## Results

The complete held-out run evaluated all 82,584 rows in `xc-temporal-2024-jan-nov-v1`.

| Model | Macro BCE ↓ | Macro Brier ↓ | Macro ROC-AUC ↑ | Monotonic violation rate ↓ |
| --- | ---: | ---: | ---: | ---: |
| Conventional MLP (seed 42) | **0.15686** | **0.04762** | **0.94206** | 0.00138 |
| TabPFN-3 ordinal | 0.16562 | 0.05128 | 0.93612 | **0.00000** |
| TabPFN-3 independent | 0.17029 | 0.05200 | 0.93562 | 0.19617 |
| Jev 1.13 | 0.31116 | 0.08475 | 0.84939 | 0.17268 |

Jev per-threshold results:

| Threshold | BCE ↓ | Brier ↓ | ROC-AUC ↑ |
| --- | ---: | ---: | ---: |
| XC0 | 0.55728 | 0.18667 | 0.78885 |
| XC10 | 0.44417 | 0.13781 | 0.82119 |
| XC20 | 0.37857 | 0.11073 | 0.83370 |
| XC30 | 0.33511 | 0.09317 | 0.84416 |
| XC40 | 0.30768 | 0.08180 | 0.84999 |
| XC50 | 0.29005 | 0.07434 | 0.86011 |
| XC60 | 0.25598 | 0.06212 | 0.86302 |
| XC70 | 0.23104 | 0.05312 | 0.86755 |
| XC80 | 0.21380 | 0.04683 | 0.86806 |
| XC90 | 0.20072 | 0.04208 | 0.87197 |
| XC100 | 0.20837 | 0.04359 | 0.87467 |
| **Macro** | **0.31116** | **0.08475** | **0.84939** |

Jev shows meaningful discrimination for a hosted decision model with no fitted Glideator weights, especially at the higher XC thresholds: ROC-AUC rises from `0.78885` at XC0 to `0.87467` at XC100. It nevertheless trails the conventional MLP on every aggregate predictive metric. Relative to the seed-42 MLP, macro BCE is worse by `0.15430`, Brier by `0.03713`, and ROC-AUC by `0.09267`.

The `0.17268` monotonic violation rate is also operationally unacceptable. It is consistent with asking eleven independent Noul questions: Jev can assign a higher probability to exceeding a harder threshold than an easier one. A post-hoc monotonic projection could remove those contradictions, but it would not repair the large ranking and probabilistic-loss gap.

The correct description is **zero-shot Jev inference over a fixed semantic adapter and fit-derived priors**, not a completely data-free weather classifier. The Jev model weights were not fitted, but the requests contain smoothed historical frequencies derived from pre-2023 rows.

## Decision

Reject Jev 1.13 as the main XC model and close this experiment line. The gap is too large to justify a prompt or representation tuning campaign, and the hosted serving constraints remain even if output consistency were repaired.

Keep the runner, pinned config and completed evaluation as a reproducible negative benchmark. Do not tune against the held-out 2024 period. The frozen conventional MLP remains the promotion reference, and the next trainable experiment returns to a materially different weather-profile encoder. See [ADR 0016](../../decisions/0016-xc-reject-jev-1-13.md).
