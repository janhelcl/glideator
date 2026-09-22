# 0016 — Do not use Jev 1.13 as the main XC model

Status: Accepted
Date: 2026-09-21

## Context

Jev 1.13 is a hosted probabilistic decision model that accepts shared semantic state and typed questions. It cannot be fine-tuned or exported into Glideator's ONNX serving path, but it offered a useful test of whether a general decision model could reason zero-shot over a niche meteorological task.

The experiment pinned `jev-1.13.0` and evaluated all 82,584 rows of `xc-temporal-2024-jan-nov-v1`. Deterministic code converted the 09:00, 12:00 and 15:00 GFS inputs into compact meteorological descriptions. Eleven independent Noul questions represented XC0 through XC100, with smoothed site/month priors computed only from pre-2023 fit rows. The 2024 labels, `max_points`, and derived targets never entered Jev state or question construction.

The tested system is therefore zero-shot Jev inference over a fixed semantic adapter and fit-derived historical priors. It is not a completely data-free weather classifier.

## Decision

Do not use Jev 1.13 as the main XC model. Do not begin a prompt or representation tuning campaign for this Jev version.

Retain the runner, pinned configuration, cached response contract and completed evaluation as a reproducible negative benchmark. The frozen conventional MLP remains the promotion reference. Resume trainable weather-specific work with a materially different profile encoder rather than another hosted-model iteration.

## Why

On the identical held-out benchmark:

| Model | Macro BCE ↓ | Macro Brier ↓ | Macro ROC-AUC ↑ | Monotonic violation rate ↓ |
| --- | ---: | ---: | ---: | ---: |
| Conventional MLP (seed 42) | **0.15686** | **0.04762** | **0.94206** | 0.00138 |
| TabPFN-3 ordinal | 0.16562 | 0.05128 | 0.93612 | **0.00000** |
| TabPFN-3 independent | 0.17029 | 0.05200 | 0.93562 | 0.19617 |
| Jev 1.13 semantic context | 0.31116 | 0.08475 | 0.84939 | 0.17268 |
| Jev 1.13 raw weather + production sites | 0.30780 | 0.08240 | 0.82614 | 0.110 |

Relative to the seed-42 conventional MLP, Jev regresses macro BCE by `0.15430`, macro Brier by `0.03713`, and macro ROC-AUC by `0.09267`. This is far beyond experiment noise or a plausible promotion margin.

Jev does contain meaningful ranking signal: per-threshold ROC-AUC increases from `0.78885` at XC0 to `0.87467` at XC100. That is a respectable result for a general hosted decision model operating in a niche domain without fitted Glideator weights, but it does not offset the aggregate loss and calibration gap.

The `0.17268` monotonic violation rate is also unacceptable for nested XC thresholds. Post-hoc projection could enforce consistency, but it cannot recover the missing discrimination or probabilistic accuracy. External latency, cost, availability, privacy and version-stability constraints further weaken the case for continued investment.

## Consequences

- Jev 1.13 is rejected for promotion and its experiment line is closed.
- Do not tune prompts or the semantic adapter against the held-out 2024 evaluation period.
- Keep `jev_1_13.yaml`, the benchmark runner and documentation for reproducibility.
- Keep the complete API response/evaluation artifacts in the experiment store; do not commit generated artifacts.
- The conventional MLP remains the XC promotion baseline.
- The next trainable architecture starts with a shared per-pressure-level encoder and ordered aggregation; attention remains a later, separate hypothesis.

## Completed bounded follow-up

After accepting this decision, review found that the first context omitted site names and takeoff wind directions and reduced the 231 weather values to a compact semantic summary. A frozen follow-up isolated that material context limitation by supplying all 231 numeric weather values plus a fingerprinted production snapshot containing 248 sites and 535 takeoffs.

The raw-context run improved macro BCE from `0.31116` to `0.30780`, Brier from `0.08475` to `0.08240`, and monotonic violation rate from `0.17268` to `0.110`. ROC-AUC fell from `0.84939` to `0.82614`. The run cost approximately `$32`.

The richer context therefore changes the trade-off but does not make Jev competitive with the frozen conventional MLP. It remains worse by `0.15094` BCE, `0.03478` Brier, and `0.11592` ROC-AUC, while its monotonic violation rate remains roughly 80 times higher. The Jev 1.13 experiment line is closed; do not continue prompt tuning or add post-hoc monotonic correction.

Because the original 2024 result had already been inspected before this follow-up was specified, the direct comparison is exploratory rather than fresh promotion evidence. The gap to the conventional baseline is nevertheless too large to affect the rejection.

## Evidence

- Benchmark: `xc-temporal-2024-jan-nov-v1`
- Evaluation rows: 82,584
- Model: `jev-1.13.0`
- Semantic prompt/state contract: `xc-semantic-weather-history-v1`
- Semantic report: `outputs/xc/baselines/jev-1.13/evaluation.json`
- Raw prompt/state contract: `xc-raw-weather-prod-sites-v2` / `raw-weather-prod-sites-v2`
- Raw report: `outputs/xc/baselines/jev-1.13-raw-prod-sites/evaluation.json`
- Model pages: [Jev 1.13 hosted challenger](../xc/models/jev.md) and [raw weather + production sites](../xc/models/jev-raw-prod-sites.md)
