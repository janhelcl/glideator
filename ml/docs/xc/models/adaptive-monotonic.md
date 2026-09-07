# Adaptive monotonic head

**Role:** active head experiment  
**Config:** `configs/xc/architecture/adaptive_monotonic.yaml`

## Hypothesis

The ordinal experiment showed that hard monotonicity is attractive but collapsing all thresholds onto one latent XC-strength axis is too restrictive. The multilabel baseline is more expressive but still produces probability inversions.

The adaptive monotonic head aims to keep both properties:

- threshold-specific, feature-conditioned behavior;
- monotonic probabilities by construction.

## Architecture

From the fused representation `h`, the head predicts one unconstrained base logit for XC0 and ten feature-conditioned positive gaps:

~~~text
base = f0(h)
gap_i = softplus(fi(h))
logit_0 = base
logit_k = base - sum(gap_1 ... gap_k)
P(XC > k) = sigmoid(logit_k)
~~~

Because every gap is positive, harder thresholds can never receive a larger logit than easier thresholds. Unlike the scalar ordinal head, each gap can vary with the weather/site representation.

The initial gap layers are initialized with zero feature weights and a modest negative bias so training starts from a smooth decreasing curve before learning feature-dependent spacing.

## Experimental baseline

This head is tested on the accepted no-CrossNet structural baseline from [ADR 0008](../../decisions/0008-xc-remove-crossnet-from-candidate-baseline.md), with the same temporal benchmark and GPU training policy.

The legacy monotonicity penalty is set to zero because the constraint is structural.

## What to learn from it

If this matches or improves calibration/discrimination while driving monotonic violations to zero, it should replace the independent multilabel head as the preferred XC output parameterization.

If it regresses materially, the remaining useful flexibility likely comes from allowing threshold logits to move more independently than cumulative positive gaps permit.

## Serving implications

The external output contract remains eleven XC threshold probabilities. ONNX export/parity is intentionally deferred until the architecture is selected from screening experiments.
