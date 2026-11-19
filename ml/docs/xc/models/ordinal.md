# Ordinal head

**Role:** rejected head experiment  
**Config:** `configs/xc/architecture/ordinal.yaml`

## Hypothesis

The eleven XC targets are nested events. A cumulative ordinal head can enforce `P(XC > 0) >= ... >= P(XC > 100)` by construction instead of relying on eleven independent sigmoid heads plus a soft monotonicity penalty.

## Architecture

The head maps the fused representation to one latent XC-strength scalar and compares it against eleven globally ordered learned thresholds.

~~~text
h -> latent score a
P(XC > k) = sigmoid(a - threshold_k)
~~~

Threshold ordering is enforced through positive cumulative `softplus` gaps.

## Result

The head removed monotonicity violations completely, but materially worsened macro BCE, Brier score and ROC-AUC in the first architecture screen.

The conclusion is not that monotonic output structure is undesirable. The failure mode is the stronger proportional-odds assumption: all thresholds are forced to depend on the representation through the same single latent axis and global threshold spacing.

The variant is not being pursued further. The follow-up adaptive monotonic head keeps hard monotonicity while allowing threshold spacing to depend on the learned weather representation.

## Serving implications

The output contract remains eleven threshold probabilities, but this architecture is rejected and is not a promotion candidate.
