# S2S model documentation

Each S2S architecture gets one short page. The page should stay stable as new runs accumulate.

## Required sections

1. **Role** — baseline, reference, ablation, or candidate.
2. **Hypothesis** — what limitation of the reference model it is testing.
3. **Architecture** — the scoring function at the level needed to reason about behavior.
4. **Delta from reference** — what changed and, equally important, what stayed fixed.
5. **Config** — canonical checked-in config.
6. **Serving contract** — whether the current backend can score the artifact.
7. **What to learn from it** — the question the experiment is intended to answer.

Do not maintain copied benchmark tables here. MLflow is the run-level system of record. If evidence leads to a durable choice — promotion, rejection, benchmark change, serving-contract change — record that conclusion in docs/decisions/.

## Current models

- [SVD](svd.md)
- [Contrastive additive](contrastive.md)
- [DeepSets](deepsets.md)
- [Asymmetric additive](asymmetric.md)
- [Transformed additive](transformed-additive.md)
- [Candidate attention](candidate-attention.md)
