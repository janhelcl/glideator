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
