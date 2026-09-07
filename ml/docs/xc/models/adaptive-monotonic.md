# Adaptive monotonic head

**Role:** rejected head experiment  
**Config:** `configs/xc/architecture/adaptive_monotonic.yaml`

## Hypothesis

The ordinal experiment showed that hard monotonicity is attractive but collapsing all thresholds onto one latent XC-strength axis is too restrictive. The multilabel baseline is more expressive but still produces probability inversions.

The adaptive monotonic head aimed to keep both properties:

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

This head was tested on the accepted no-CrossNet structural baseline from [ADR 0008](../../decisions/0008-xc-remove-crossnet-from-candidate-baseline.md), with the same temporal benchmark and GPU training policy.

The legacy monotonicity penalty was set to zero because the constraint is structural.

## Result

The matched seed-42 run finished with zero monotonicity violations, but regressed against the no-CrossNet multilabel baseline on all three primary predictive metrics:

| Metric | Adaptive monotonic | No-CrossNet |
| --- | ---: | ---: |
| Macro BCE | 0.16209 | 0.15982 |
| Macro Brier | 0.04912 | 0.04848 |
| Macro ROC-AUC | 0.93601 | 0.93944 |
| Monotonic violation rate | 0.0000 | 0.0199 |
| Trainable parameters | 64,267 | 64,267 |

MLflow run: `4753c267f3f447cb8eb19a2f8e406ff8` (`rumbling-mink-438`).

The experiment bar was to match or improve calibration/discrimination while driving violations to zero. It met the monotonicity requirement and missed the predictive-quality requirement.

## Decision

Rejected. Do not spend a seed sweep or width tuning on this formulation.

The result is much better than the scalar ordinal head, so feature-conditioned threshold spacing recovered useful flexibility, but cumulative positive gaps still constrain the output layer enough to hurt calibration and discrimination.

The no-CrossNet multilabel head remains the candidate baseline. See [ADR 0009](../../decisions/0009-xc-reject-hard-monotonic-heads.md).

## Serving implications

The external output contract would remain eleven XC threshold probabilities, but this head is not a promotion candidate. ONNX export/parity is therefore unnecessary unless the architecture is revisited under a new hypothesis.
