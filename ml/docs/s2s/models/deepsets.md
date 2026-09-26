# DeepSets

**Role:** nonlinear history-encoder experiment  
**Config:** configs/s2s/deepsets.yaml  
**Serving:** requires scorer-aware serving

## Hypothesis

A plain sum of site embeddings may be too restrictive. A learned permutation-invariant set encoder may capture interactions among a pilot's discovered sites.

## Architecture

Each history site is transformed by phi, pooled, then passed through rho:

~~~text
query = rho(pool(phi(site_1), ..., phi(site_n)))
~~~

The checked-in configuration uses mean pooling. The candidate catalogue still uses normalized site embeddings.

## Delta from contrastive additive

Changed:

- nonlinear per-site phi network;
- pooling before a nonlinear rho network.

Kept aligned in the canonical comparison:

- benchmark identity;
- embedding dimension;
- optimizer and contrastive objective;
- negative-sampling policy;
- candidate representation.

## Serving contract

The artifact preserves the legacy keys but adds the learned phi/rho weights in scorer. Experiment evaluation uses this scorer.

Do not promote the artifact to the current backend until serving executes the same learned history encoder.

## What to learn from it

DeepSets tests whether the missing ingredient is **nonlinear interaction after pooling**. Compare it especially with transformed additive, which keeps the nonlinear per-site transform but removes the post-pooling bottleneck.
