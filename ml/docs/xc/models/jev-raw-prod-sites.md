# Jev 1.13 raw weather + production site context

## Hypothesis

The first Jev experiment compressed the weather profile into a small semantic summary and exposed only numeric site ID, coordinates and altitude. It omitted the site name and takeoff wind directions and discarded much of the canonical 231-value forecast.

This bounded follow-up asks whether Jev's result was constrained primarily by that representation. Model version, target questions, historical priors, temporal split and evaluator remain fixed. Only the shared state changes.

## Frozen context contract

The executable config is `configs/xc/baselines/jev_1_13_raw_prod_sites.yaml`.

For each site/date request, state contains:

- the production site name plus benchmark latitude, longitude and altitude;
- every takeoff stored for that site in the frozen production snapshot;
- each takeoff's name, coordinates, altitude and suitable wind-direction range;
- exact date, year, month, day of year, season and weekend flag;
- all 77 canonical GFS values at 09:00, 12:00 and 15:00;
- explicit unit conventions for the machine-readable feature names.

The 231 weather values remain numeric and are not categorized or selectively dropped. Temperatures remain Kelvin, pressure remains pascals, wind components remain m/s, humidity remains percent, and geopotential height remains metres above mean sea level.

The site snapshot is `data/xc/jev_site_context_prod_2026-09-21.json`, exported read-only from the production `public.sites` and `public.spots` tables on 2026-09-21. It contains 248 sites and 535 takeoffs for `site_id <= 250`. Its content fingerprint is part of the response-cache contract.

## What remains unchanged

- model: pinned `jev-1.13.0`;
- benchmark: `xc-temporal-2024-jan-nov-v1`;
- prior-fit rows: before `2023-01-01`;
- 2023 excluded from priors and final evaluation;
- eleven independent Noul questions for strict `XC0` through `XC100`;
- smoothed same-site/month, same-site and global occurrence frequencies;
- standard BCE, Brier, ROC-AUC and monotonicity evaluation;
- append-only responses, resumability and complete-only MLflow logging.

No `max_points`, evaluation label or derived target enters state construction.

## Running

~~~bash
cd ml
pip install -e '.[jev,tracking]'
export ML_DATABASE_URL='postgresql://...'
export TYPESAFE_API_KEY='...'

glideator-ml benchmark-jev xc \
  --config configs/xc/baselines/jev_1_13_raw_prod_sites.yaml \
  --limit 100
~~~

Inspect `evaluation.partial.json`, especially input tokens, projected full cost, latency and failures. Continue the same cache only if the smoke run is healthy:

~~~bash
glideator-ml benchmark-jev xc \
  --config configs/xc/baselines/jev_1_13_raw_prod_sites.yaml
~~~

## Interpretation boundary

This is one pre-specified context ablation, not an open prompt-tuning loop. The original 2024 result was already inspected before this follow-up was designed, so the repeated 2024 score is useful for direct exploratory comparison but is not fresh promotion evidence.

Do not alter this prompt/state contract after seeing partial or full 2024 metrics. Any promotion claim would require a new untouched time period in addition to the hosted-serving review.
