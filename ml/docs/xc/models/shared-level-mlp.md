# Shared pressure-level MLP

**Role:** active weather-profile architecture experiment  
**Config:** `configs/xc/architecture/weather_profiles/shared_level_mlp.yaml`

## Hypothesis

The flat conventional weather tower must learn both within-level atmospheric
relationships and vertical structure at once. The rejected Conv1D family added
a strong local-adjacency assumption that did not survive paired-seed
confirmation. A shared per-level encoder is a simpler alternative: learn the
same nonlinear representation at every pressure surface, then let an ordered
projection combine the resulting level tokens.

## Architecture

For each of 09:00, 12:00 and 15:00, the candidate selects the canonical
standardized profile `[u, v, T, RH, z]` at 13 pressure levels ordered from 1000
to 500 hPa:

~~~text
[batch, 5 variables, 13 levels]
  -> transpose to [batch, 13 levels, 5 variables]
  -> shared MLP 5 -> 16 -> 8 at every level
  -> ordered flatten of 13 x 8 tokens
  -> Linear(104 -> 32)
  -> 32d profile embedding
~~~

The encoder weights are shared across pressure levels and across the three
forecast times. Ordered flattening preserves level identity without adding
attention or convolution.

The profile branch is additive. The frozen conventional raw bypass, shared
per-time MLP `[64, 32]`, fusion `[64, 32]`, 32d site embedding, independent
sigmoid head, dropout `0.10`, optimizer policy and benchmark remain unchanged.

## Experiment policy

Run seed 42 as a cheap screen against `conventional_mlp.yaml`. Only a coherent
improvement in the primary BCE/Brier metrics without a material ROC-AUC
regression earns paired confirmation on seeds 42–46. Seed 42 alone is not
promotion evidence.

Do not add AGL/masking or level attention to this first run. They are separate
representation hypotheses. If the shared level encoder shows repeatable signal,
attention across level tokens is the next experiment.

## Serving implications

Inputs and outputs are unchanged. The candidate remains an experiment artifact
until paired-seed confirmation and the normal ONNX promotion gate both pass.
