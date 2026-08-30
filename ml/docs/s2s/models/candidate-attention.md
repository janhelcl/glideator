# Candidate attention

**Role:** candidate-conditioned residual experiment  
**Config:** configs/s2s/candidate-attention.yaml  
**Serving:** requires scorer-aware serving

## Hypothesis

A single global history vector forces every candidate to interpret the pilot's history in the same way. A candidate may instead care about different visited sites.

## Architecture

The normalized additive history remains the residual base.

For each candidate, a single attention head uses learned Q/K/V projections to weight history sites and produce a candidate-specific context. A learned scalar controls the correction:

~~~text
candidate_query = normalize(additive_base + attention_scale * context(candidate, history))
score(candidate) = cosine(candidate_query, candidate_embedding)
~~~

The attention scale is initialized small so training starts close to the strong additive reference.

The S2S catalogue is only a few hundred sites, so candidate-conditioned full-catalogue scoring is tractable.

## Delta from contrastive additive

The additive representation is retained as a residual path. The only new capability is a candidate-specific correction over the visited-site set.

## Serving contract

The artifact stores history embeddings, Q/K/V weights, and attention_scale in scorer. Current production inference does not execute this scorer.

## What to learn from it

This tests whether candidate-specific interpretation of history adds value without discarding the additive inductive bias.
