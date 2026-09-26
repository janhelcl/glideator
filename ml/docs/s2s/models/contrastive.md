# Contrastive additive

**Role:** production-equivalent neural reference  
**Configs:** configs/s2s/contrastive-prod-equivalent.yaml and configs/s2s/contrastive-temporal-v2.yaml  
**Serving:** compatible with the current backend

## Hypothesis

A pilot's discovered sites can be represented well by a normalized additive embedding, trained directly to separate the next first-visit target from sampled negatives.

## Architecture

A single site embedding table is shared between history and candidate representations.

For a training episode:

~~~text
query = normalize(sum(embedding(history_sites)))
positive = normalize(embedding(target_site))
~~~

The loss contrasts the positive against sampled negative sites using temperature-scaled cross entropy.

The checked-in production-equivalent configuration uses popularity-powered negative sampling. History sites and the positive target are excluded from sampled negatives. In-batch negatives are configurable.

## Why this is the reference

The additive representation is simple, permutation-invariant, fast to score over the whole catalogue, and matches the current production artifact contract.

Every experimental neural architecture should state exactly which part of this reference it changes while keeping benchmark and training policy aligned.

## What to learn from it

This is the main neural comparison point and the serving-compatible fallback. New architectures should beat it for a clear reason, not merely add capacity.
