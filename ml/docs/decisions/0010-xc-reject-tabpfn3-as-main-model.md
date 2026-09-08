# 0010 — Do not replace the XC model with TabPFN-3

Status: Accepted
Date: 2026-09-08

## Context

The XC model is a specialized neural model trained on the canonical temporal benchmark `xc-temporal-2024-jan-nov-v1`. After simplifying the architecture and removing CrossNet, the strongest refinement used a smaller shared encoder with eleven independent sigmoid threshold heads.

To test whether a current frontier tabular foundation model could provide a stronger baseline or replacement, TabPFN-3 (`tabpfn==8.5.0`, model v3) was evaluated with the same raw feature information, temporal split, fit-parity context rows and standard XC evaluator.

Two TabPFN-3 target formulations were tested:

1. **Ordinal multiclass**: the eleven nested XC labels were encoded losslessly as one 12-class target, then converted back to `P(XC0)` through `P(XC100)` using cumulative class probabilities. This guarantees monotonic predictions.
2. **Independent binary**: eleven separate TabPFN-3 classifiers were fit independently, one for each XC threshold. This provides the closest objective-level comparison with the existing multilabel neural head.

The matched benchmark results were:

| Model | Macro BCE | Macro Brier | Macro ROC-AUC | Monotonic violation rate |
| --- | ---: | ---: | ---: | ---: |
| Smaller encoder refinement | 0.15787 | 0.04788 | 0.94098 | 0.0270 |
| No-CrossNet control | 0.15982 | 0.04848 | 0.93944 | 0.0199 |
| TabPFN-3 ordinal | 0.16562 | 0.05128 | 0.93612 | 0.0000 |
| TabPFN-3 independent | 0.17029 | 0.05200 | 0.93562 | 0.1962 |

Before accepting the result, the TabPFN context path was checked for shortcuts that could unfairly handicap the foundation model. The final runs used:

- `181,040` context rows, exactly equal to the neural fit partition;
- `90,520` additional calendar-2023 rows held out as the neural model-selection partition;
- `82,584` final evaluation rows;
- all `248` sites represented in both context and evaluation;
- the full raw XC feature contract of `239` columns;
- `SUBSAMPLE_SAMPLES=None`, so TabPFN did not subsample context rows internally;
- `MAX_NUMBER_OF_SAMPLES=1,000,000` and `MAX_NUMBER_OF_FEATURES=2,000`, so the run was within the configured v3 limits;
- the standard v3 ensemble behavior of eight estimators with at most 200 features per estimator. Because the table has 239 columns and more than 100k rows, TabPFN's automatic feature-subsampling policy resolves to importance-based feature selection. This is part of the default TabPFN inference strategy, not a benchmark-specific shortcut.

The ordinal and independent runs have the same `context_fingerprint`, `dataset_fingerprint` and `eval_set_fingerprint`.

## Decision

Do not pursue TabPFN-3 as a replacement for the specialized XC neural model on the current benchmark.

Keep the specialized shared neural representation as the main XC modeling direction. The TabPFN benchmark implementation may remain in the repository as a reference challenger, but further TabPFN tuning is not a priority without a materially new hypothesis.

Do not run an additional `all_pre_eval` TabPFN benchmark solely to give the foundation model the calendar-2023 model-selection rows. The accepted comparison intentionally uses fit-parity label exposure: TabPFN sees the same `181,040` rows used to fit neural weights. Giving it the additional `90,520` validation labels would answer a different, best-case in-context question rather than the replacement question this benchmark was designed to answer.

Do **not** interpret this decision as a rejection of the 12-class ordinal target formulation for the neural model. The next target-formulation experiment should apply the same lossless 12-class softmax formulation to the strongest specialized encoder while keeping the representation and benchmark fixed.

## Why

Both TabPFN-3 formulations underperform the specialized neural models on calibration and discrimination.

Against the smaller-encoder refinement, the stronger TabPFN variant (ordinal) is worse on all three primary predictive metrics:

- macro BCE: `0.16562` vs `0.15787`;
- macro Brier: `0.05128` vs `0.04788`;
- macro ROC-AUC: `0.93612` vs `0.94098`.

The objective-parity experiment also rules out the hypothesis that TabPFN was being held back mainly by the ordinal formulation. Eleven independent TabPFN classifiers perform worse still: macro BCE rises to `0.17029`, macro Brier to `0.05200`, and macro ROC-AUC falls to `0.93562`.

The context audit removes the main fairness concern. TabPFN received every row in the neural fit partition and performed no hidden row subsampling. The only intentionally unavailable labels were the same calendar-2023 labels reserved for neural model selection. The per-estimator 200-feature cap is standard v3 ensemble behavior and was left untouched so the benchmark reflects the shipped foundation model rather than a custom inference configuration.

The independent TabPFN result also reveals a useful structural difference. Its monotonic violation rate is `0.1962`, compared with only `0.0199` for the No-CrossNet neural model even though the neural outputs are also nominally independent. The shared neural encoder and fusion representation therefore induce substantial cross-threshold consistency without a hard monotonic constraint.

At the same time, the TabPFN ordinal formulation materially improves over TabPFN independent and removes monotonic violations entirely. That is evidence that the target formulation itself is worth isolating inside our stronger specialized model. It does not rescue TabPFN as the model family, but it motivates completing the model-by-formulation matrix before closing the ordinal question.

Runtime reinforces the decision not to spend more budget on the independent foundation-model path: the ordinal benchmark took about `3,135 s` end-to-end, while eleven independent classifiers took about `34,021 s` (roughly 9.4 hours), almost all of it prediction time.

## Consequences

- The specialized neural XC model remains the primary modeling direction.
- The smaller-encoder refinement remains stronger than both TabPFN-3 challengers on the current benchmark.
- Stop spending experiment budget on routine TabPFN-3 tuning, additional seeds, wider-context reruns or serving integration unless a new hypothesis justifies reopening the comparison.
- Retain the TabPFN configs and runner as reproducible external baselines.
- Run the missing fourth experiment: strongest neural encoder with a lossless 12-class softmax target and cumulative threshold reconstruction.
- Continue evaluating any ordinal neural formulation with the same macro/per-threshold BCE, Brier, ROC-AUC and monotonicity metrics; perfect monotonicity is not sufficient for promotion.
- Do not use the poor monotonicity of eleven independent TabPFNs as an argument for hard constraints in the neural model: the existing shared representation already produces much more coherent threshold probabilities.

## Evidence

- Benchmark: `xc-temporal-2024-jan-nov-v1`.
- Ordinal TabPFN MLflow run: `34d9b960aa23495da8b16150dd04051d`.
- Independent TabPFN MLflow run: `dd8f3fb974cc49a4a0529d0677fdbb56`.
- Ordinal TabPFN config: `configs/xc/baselines/tabpfn3.yaml`.
- Independent TabPFN config: `configs/xc/baselines/tabpfn3_independent.yaml`.
- TabPFN benchmark runner: `glideator_ml/xc/tabpfn.py`.
- Ordinal artifacts: `outputs/xc/baselines/tabpfn3/`.
- Independent artifacts: `outputs/xc/baselines/tabpfn3-independent/`.
- Related decision: [ADR 0009](0009-xc-reject-hard-monotonic-heads.md).
