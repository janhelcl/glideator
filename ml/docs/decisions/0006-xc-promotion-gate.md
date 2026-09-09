# 0006 — Gate XC promotion on identical benchmark identity and explicit regressions

Status: Accepted
Date: 2026-09-06

## Context

The XC migration now produces a trained checkpoint/ONNX candidate and can score the currently served ONNX artifact on the same temporal benchmark. A deployment decision must not rely on visually comparing two MLflow runs that may have used different source rows, feature ordering, or evaluation sets.

The migration also needs a clear distinction between model quality and serving-format correctness. A candidate can score well but still be unsafe to serve if its exported ONNX does not reproduce its PyTorch outputs.

## Decision

XC promotion uses a machine-readable comparison gate.

Before quality metrics are compared, candidate and reference reports must match exactly on:

- `benchmark_id`;
- `dataset_fingerprint`;
- `eval_set_fingerprint`;
- the complete `feature_contract`.

A candidate is not promotion-eligible if any of those identities differ.

The candidate must also contain an exported ONNX artifact whose measured PyTorch ↔ ONNX maximum absolute difference is within the explicitly configured parity tolerance.

Quality rules are configuration, not hidden code defaults. Each blocking metric declares:

- whether lower or higher is better;
- the maximum absolute regression allowed versus the served reference.

For the initial compatibility migration, `xc_production_reference.yaml` uses a strict no-regression policy for:

- macro BCE;
- macro Brier score;
- macro ROC-AUC.

The comparator writes `promotion.json` and exits non-zero when the candidate is not eligible. Passing this gate means only that the artifact is eligible for an explicit serving change; it does not deploy or replace the backend artifact automatically.

## Why

A fixed benchmark is useful only if both artifacts are proven to have run on the same benchmark instance. Fingerprints make that check mechanical rather than procedural.

Keeping tolerances in config makes any relaxation visible in code review and tied to a specific experiment policy. Separating ONNX parity from benchmark quality prevents a model-format bug from being hidden by otherwise acceptable metrics.

## Consequences

- Candidate/reference reports from different data snapshots or evaluation rows cannot be compared for promotion.
- Promotion thresholds can change only through an explicit config change.
- The first migration gate is intentionally conservative: a newly trained replacement must not regress the selected benchmark metrics.
- Backend deployment remains a separate step after the gate passes.
- Future model changes may adopt different promotion rules, but must record the policy change if it alters interpretation of benchmark comparisons.

## Evidence

- `glideator_ml.xc.promotion`
- `configs/xc_production_reference.yaml`
- PR #115
