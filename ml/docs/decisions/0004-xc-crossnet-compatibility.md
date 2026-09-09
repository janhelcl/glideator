# 0004 — Preserve XC CrossNet compatibility without TorchRec

Status: Accepted
Date: 2026-09-06

## Context

The production XC model was built against Torch 2.4.1, TorchRec 0.8.0 and FBGEMM. The newer `ml/` workspace already uses a newer Torch line for S2S experiments. Carrying the old TorchRec stack into the shared ML workspace would couple unrelated model families to an obsolete dependency combination and make the XC migration harder to maintain.

The XC architecture only uses TorchRec's full-rank `CrossNet`. Its forward equation and state are small: each layer owns a square `kernels` matrix and column `bias`, and applies the standard explicit feature-cross recurrence.

## Decision

The migrated XC task will use a local pure-PyTorch `CrossNet` that preserves the legacy implementation's:

- forward equation;
- `kernels.<layer>` and `bias.<layer>` state-dict names;
- parameter shapes;
- surrounding `ExpandedGlideatorNet` module layout.

The new `ml/` package will not take a TorchRec or FBGEMM dependency for XC.

Legacy XC state dicts are a compatibility input. Legacy full-object PyTorch pickles are not: they remain tied to the old module path and dependency environment.

## Why

This removes an unnecessary dependency conflict while keeping the model migration numerical rather than architectural. It also gives the XC task ownership of the small primitive it actually needs and makes eventual checkpoint parity testable without booting the legacy TorchRec environment for every experiment.

## Consequences

- A compatibility test must lock the CrossNet parameter names, shapes and recurrence.
- Loading a production-era state dict into the migrated architecture should be part of the XC parity gate.
- Production promotion must compare outputs from the migrated model and current serving artifact on identical inputs.
- Changing the CrossNet equation or state layout is a model/artifact-contract change, not a refactor.
- The old full-object pickle format should not become the artifact contract of the new XC workspace.

## Evidence

The first XC migration slice in PR #115 reproduces the production CrossNet contract in `glideator_ml.xc.model` and covers it with synthetic contract tests.
