# ML decision records

Decision records preserve reasoning that should still matter after individual experiment runs are forgotten.

They are intentionally lighter than a formal architecture-governance process.

## Record a decision when

A choice changes one or more of:

- benchmark semantics or identity;
- train/evaluation leakage guarantees;
- shared experiment policy;
- artifact or serving contracts;
- promotion criteria;
- the interpretation of future model comparisons.

Do **not** create a decision record for every model run or hyperparameter sweep. Those belong in MLflow.

A model-specific hypothesis belongs on the model page. If the experiment produces a durable conclusion — for example "do not pursue post-pooling DeepSets for S2S" or "promote architecture X" — add a decision record that cites the relevant MLflow run IDs.

## Template

~~~text
# NNNN — Decision title

Status: Proposed | Accepted | Superseded
Date: YYYY-MM-DD

## Context
What problem or ambiguity forced the decision?

## Decision
What is now the rule?

## Why
Why this choice over the alternatives?

## Consequences
What becomes easier, harder, required, or forbidden?

## Evidence
Optional MLflow run IDs, reports, PRs, or code references.
~~~

## Current records

- [0001 — Stable benchmark identity](0001-stable-benchmark-identity.md)
- [0002 — Task-owned semantics](0002-task-owned-semantics.md)
- [0003 — Scorer-aware artifacts](0003-scorer-aware-artifacts.md)
- [0004 — Preserve XC CrossNet compatibility without TorchRec](0004-xc-crossnet-compatibility.md)
- [0005 — Use a fixed temporal benchmark for XC](0005-xc-temporal-benchmark.md)
- [0006 — Gate XC promotion on identical benchmark identity and explicit regressions](0006-xc-promotion-gate.md)
- [0007 — Use batch size 8192 for XC GPU experiments](0007-xc-gpu-batch-policy.md)
- [0008 — Remove CrossNet from the XC candidate baseline](0008-xc-remove-crossnet-from-candidate-baseline.md)
- [0009 — Do not use hard monotonic output heads as the XC candidate baseline](0009-xc-reject-hard-monotonic-heads.md)
- [0010 — Do not replace the XC model with TabPFN-3](0010-xc-reject-tabpfn3-as-main-model.md)
- [0011 — Promote the smaller shared encoder as the XC conventional baseline](0011-xc-promote-smaller-shared-encoder.md)
- [0012 — Keep a 32-dimensional XC site embedding](0012-xc-keep-32d-site-embedding.md)
- [0013 — Freeze the optimized XC conventional benchmark](0013-xc-freeze-optimized-conventional-benchmark.md)
