# Expanded production reference

## Role

This is the compatibility baseline for migrating Glideator's currently served XC model family. It is not a new architecture proposal.

The executable config is `configs/xc_production_reference.yaml`.

## Architecture

For each of 09:00, 12:00 and 15:00 the model concatenates:

- 77 scaled GFS features;
- scaled site latitude, longitude and altitude;
- a 32-dimensional learned site embedding;
- four date features.

That produces 116 inputs per time slice. The exact served architecture is derived from `backend/app/models/model.onnx`, not from notebook examples:

1. a shared two-layer full-rank CrossNet processes the 116 inputs;
2. a shared parallel deep tower `[128, 64, 32]` processes the same inputs;
3. the 116-dimensional cross output and 32-dimensional parallel output are concatenated, producing 148 values per time slice;
4. the three time slices are concatenated into 444 values;
5. the main deep tower `[64, 32]` produces the representation consumed by eleven independent sigmoid heads for `XC0` through `XC100`.

The model has 251 embedding slots, matching site IDs 0–250.

`glideator_ml.xc.compatibility` infers this constructor contract directly from ONNX parameter names/shapes and reconstructs the migrated PyTorch model with the exact weights embedded in the served artifact. CI then compares that model numerically with ONNX Runtime on identical production-shaped inputs.

## Migration-specific delta

The only intentional architecture implementation change is replacing TorchRec's `CrossNet` with `glideator_ml.xc.model.CrossNet`. The replacement preserves the full-rank equation and legacy state-dict parameter names/shapes.

No prediction semantics are intentionally changed in this reference model.

## Training contract

- strict targets: `max_points > threshold`;
- summed BCE across the eleven heads;
- optional adjacent-threshold monotonicity penalty;
- Adam optimizer and exponential LR decay;
- weather scaler fitted from 12:00 fit features and reused at all three times;
- site scaler fitted from fit rows only;
- rows before 2023 used for fitting, 2023 for model selection, and 2024 held out for final evaluation.

The stable comparison benchmark is `xc-temporal-2024-v1`, not the old random `is_validation` split.

Historical optimizer trajectory, stochastic seed and exact stopping epoch cannot be recovered from the served ONNX and are therefore explicit migrated experiment policy rather than claimed production facts.

## Serving implications

The migrated ONNX keeps the current six-input serving interface and eleven-output target order. Candidate export must pass PyTorch ↔ ONNX Runtime parity before comparison with the served reference.

The generated checkpoint and ONNX remain experiment artifacts until the candidate passes the task-owned promotion policy and an explicit backend artifact switch is made.
