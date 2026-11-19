# No-CrossNet baseline

**Role:** accepted structural baseline for new XC candidates  
**Config:** `configs/xc/architecture/no_cross.yaml`

## Hypothesis

The production-shaped model inherited a full-rank CrossNet from the legacy architecture. With the current atmospheric representation and parallel deep tower, explicit polynomial feature crossing may be redundant or harmful.

## Architecture

The model keeps the production-shaped data path, site embedding, shared per-time deep tower, three time slices, fusion MLP `[64, 32]`, and multilabel prediction head.

The only structural change from the migrated control is:

~~~text
cross_layers: 2  ->  cross_layers: 0
~~~

With zero CrossNet layers the raw combined per-time representation is passed directly alongside the parallel deep tower output.

## Result

The initial architecture screen favored this variant. A paired seed sweep over model seeds 42–46 then confirmed a small calibration improvement, effectively tied discrimination, a large reduction in monotonicity violations, and fewer parameters versus the CrossNet control.

This is therefore the baseline for subsequent XC architecture experiments. See [ADR 0008](../../decisions/0008-xc-remove-crossnet-from-candidate-baseline.md).

## Serving implications

No new input or output contract is introduced. If ultimately promoted, the candidate can use the same six-input / eleven-output serving shape after normal ONNX parity validation.
