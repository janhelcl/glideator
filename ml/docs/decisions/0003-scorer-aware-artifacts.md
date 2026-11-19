# 0003 — Preserve the legacy S2S artifact and extend with scorer state

**Status:** Accepted  
**Date:** 2026-08-30

## Context

The production S2S backend currently expects a simple pickle payload built around site_to_idx, idx_to_site, and matrix. That is sufficient for SVD and the additive contrastive model.

Experimental architectures such as DeepSets, asymmetric embeddings, transformed additive, and candidate attention require additional learned state to reproduce training-time scoring.

Breaking the artifact contract for every experiment would make comparisons and future promotion unnecessarily expensive. Pretending every model can be reduced to matrix alone would make evaluation inconsistent with serving behavior.

## Decision

All S2S artifacts preserve the legacy keys:

~~~text
site_to_idx
idx_to_site
matrix
~~~

Architectures that need extra inference state add an optional scorer payload.

The experiment evaluator must use scorer when present so evaluation matches the model that was actually trained.

An artifact that requires scorer is **not production-compatible** until backend serving implements that scorer type.

## Why

This keeps backward compatibility for simple models while allowing experimentation with richer scoring functions without lying about inference equivalence.

## Consequences

- SVD and additive contrastive artifacts remain directly compatible with current serving.
- New scorer types require validation and round-trip tests.
- Promotion of scorer-based models must include an explicit serving change.
- Artifact compatibility is documented on every model page.
