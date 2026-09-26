# Asymmetric additive

**Role:** representation-tie ablation  
**Config:** configs/s2s/asymmetric.yaml  
**Serving:** requires scorer-aware serving

## Hypothesis

A site may need a different representation when it appears in a pilot's history than when it is scored as a future candidate. Sharing one embedding table forces those two roles together.

## Architecture

History and candidates use separate embedding tables:

~~~text
query = normalize(sum(source_embedding(history_sites)))
score(candidate) = cosine(query, target_embedding(candidate))
~~~

History composition remains purely additive.

## Delta from contrastive additive

The only architectural change is untied source and target embeddings. The additive history function and contrastive training structure remain unchanged.

That makes the model a focused test of **representation asymmetry**, rather than a test of additional history-encoder capacity.

## Serving contract

Target embeddings remain in matrix. The source embedding table is stored in scorer.source_matrix.

Current production serving assumes the same matrix is used for history and candidates, so this artifact needs scorer-aware inference.

## What to learn from it

Use this ablation to decide whether the shared-embedding constraint itself is limiting the reference model.
