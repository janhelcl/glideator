# 0011 — Promote the smaller shared encoder as the XC conventional baseline

Status: Accepted
Date: 2026-09-08

## Context

After removing CrossNet and retaining the independent multilabel output head, the next XC architecture screen tested whether the inherited per-time representation was unnecessarily large. The accepted no-CrossNet control used a shared per-time encoder `[128, 64, 32]` plus the raw per-time bypass and fusion tower `[64, 32]`.

The refinement screen changed one representation/capacity hypothesis at a time. The strongest seed-42 candidate reduced the shared per-time encoder to `[64, 32]` while keeping the benchmark, raw bypass, fusion tower, site embedding, optimizer and output head unchanged.

Because the seed-42 gain was modest enough to require confirmation, the control and smaller encoder were rerun on paired model seeds 42–46 against `xc-temporal-2024-jan-nov-v1`.

## Decision

Use the shared per-time encoder `[64, 32]` as the conventional XC architecture baseline for subsequent generic optimization experiments.

Keep the rest of the accepted architecture unchanged for now:

- no CrossNet (`cross_layers: 0`);
- raw per-time input bypass retained;
- shared encoder weights across 09/12/15;
- fusion tower `[64, 32]`;
- site embedding dimension `32` until separately optimized;
- independent multilabel sigmoid head;
- batch size `8192`.

## Why

Across paired seeds 42–46, the smaller encoder won every seed on all three primary predictive metrics:

| Metric | Control mean | Smaller encoder mean | Candidate delta | Candidate wins |
| --- | ---: | ---: | ---: | ---: |
| Macro BCE ↓ | 0.16091 | 0.15764 | -0.00328 | 5/5 |
| Macro Brier ↓ | 0.04864 | 0.04785 | -0.00079 | 5/5 |
| Macro ROC-AUC ↑ | 0.93891 | 0.94098 | +0.00207 | 5/5 |

The candidate also reduces trainable parameters from roughly 64k to 48.5k.

Its mean monotonic-violation rate increased from 0.0165 to 0.0253 and it won that diagnostic only 1/5 seeds. This does not override the promotion because monotonicity is a secondary diagnostic, while prior hard-monotonic head experiments showed a consistent loss in predictive quality when enforcing zero violations structurally.

## Consequences

- New conventional XC optimization experiments start from `[64, 32]`, not `[128, 64, 32]`.
- The old refinement control remains only as a reproducibility record.
- Site-embedding size is the next isolated optimization question.
- Future weather-specific architectures must beat the tuned conventional baseline, not the older production-shaped architecture.
- Monotonicity violations continue to be measured and reported but are not a hard promotion gate.

## Evidence

Paired seed confirmation, seeds 42–46, benchmark `xc-temporal-2024-jan-nov-v1`:

- BCE: `0.16091 → 0.15764`, 5/5 wins;
- Brier: `0.04864 → 0.04785`, 5/5 wins;
- ROC-AUC: `0.93891 → 0.94098`, 5/5 wins;
- monotonic violation rate: `0.0165 → 0.0253`, 1/5 wins.

Run-level metrics and identifiers remain in MLflow; `paired_comparison.json` is emitted by the reusable `confirm-seeds` runner.
