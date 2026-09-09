# Transformed additive

**Role:** nonlinear additive ablation  
**Config:** configs/s2s/transformed-additive.yaml  
**Serving:** requires scorer-aware serving

## Hypothesis

DeepSets adds two ideas at once: nonlinear per-site transforms and a nonlinear post-pooling encoder. If DeepSets underperforms, the post-pooling compression may be the problem rather than nonlinearity itself.

## Architecture

Each site is transformed independently and the transformed vectors are summed:

~~~text
query = sum(rho(phi(site_i)))
~~~

The final query is normalized before cosine scoring.

With a one-site history this has the same functional form as the DeepSets transform path. With longer histories it preserves additive composition instead of applying rho after pooling.

## Delta from DeepSets

Changed:

~~~text
rho(mean(phi(site_i)))  ->  sum(rho(phi(site_i)))
~~~

The canonical config keeps the same phi/rho dimensions and aligns the remaining contrastive training policy with the reference comparison.

## Serving contract

The artifact stores the phi/rho weights in scorer and therefore requires scorer-aware serving.

## What to learn from it

This isolates whether **nonlinear per-site representation** helps while **post-pooling nonlinear compression** hurts.
