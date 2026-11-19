# 0008 — Remove CrossNet from the XC candidate baseline

Status: Accepted
Date: 2026-09-07

## Context

The migrated production-shaped XC model applies a shared two-layer full-rank CrossNet independently to the 09:00, 12:00 and 15:00 feature slices. The first controlled architecture sweep tested whether this explicit crossing remains useful once the model is trained under the reproducible temporal benchmark.

A single-seed screen found `cross_layers: 0` was the only structural ablation to improve macro BCE, macro Brier and macro ROC-AUC simultaneously while also reducing monotonicity violations and parameter count.

Because the improvements were small, the result was verified with paired seeds 42–46 for the production-shaped control and the no-CrossNet variant.

Across five seeds, no-CrossNet won BCE 4/5 times, Brier 4/5 times, AUC 3/5 times, and monotonicity 5/5 times. Mean AUC was effectively tied, while calibration improved modestly and the monotonicity-violation rate dropped substantially.

## Decision

Use the no-CrossNet architecture (`cross_layers: 0`) as the structural baseline for new XC candidate experiments.

Do not spend further candidate-model capacity on shared or time-specific full-rank CrossNets unless new evidence justifies reopening the decision.

Keep the CrossNet implementation only where required for compatibility with the currently served/reference model family.

## Why

The paired-seed evidence shows no discrimination benefit from CrossNet, while removing it:

- improves mean macro BCE from about 0.16223 to 0.16091;
- improves mean macro Brier from about 0.04882 to 0.04864;
- leaves mean macro ROC-AUC effectively unchanged (0.93895 vs 0.93891);
- reduces mean monotonicity violations from about 0.0473 to 0.0165;
- reduces trainable parameters from about 91k to 64k.

The first sweep also tested unshared time-specific CrossNets, which regressed versus the control. That makes excessive sharing an unlikely explanation; explicit crossing itself appears unnecessary for this representation.

## Consequences

- `cross_layers: 0` is the starting point for subsequent XC head and capacity experiments.
- New candidate configs should not carry CrossNet as a default knob merely for historical compatibility.
- The legacy-compatible CrossNet code remains until served/reference artifact compatibility no longer requires it.
- ADR 0004 is not superseded: it still governs compatibility reconstruction of the old model family. This decision governs future candidate architecture.

## Evidence

- Initial architecture screen: `outputs/xc/architecture/`
- Paired seed sweep (42–46): `outputs/xc/architecture/seeds/`
- Mean paired deltas vs control: BCE −0.0013, Brier −0.00018, AUC approximately 0, monotonicity rate −0.031.
