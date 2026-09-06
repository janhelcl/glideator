# Expanded production reference

## Role

This is the compatibility baseline for migrating Glideator's currently served XC model family. It is not a new architecture proposal.

The executable config is `configs/xc_production_reference.yaml`.

## Architecture

For each of 09:00, 12:00 and 15:00 the model concatenates:

- 77 scaled GFS features;
- scaled site latitude, longitude and altitude;
- a learned site embedding;
- four date features.

A shared two-layer full-rank cross network processes each time slice. The three outputs are concatenated and passed through hidden layers `[128, 64, 32]`, followed by eleven independent sigmoid heads for `XC0` through `XC100`.

The reference configuration uses a 32-dimensional site embedding and 251 embedding slots, matching the historical site-ID domain 0–250.

## Migration-specific delta

The only intentional architecture implementation change is replacing TorchRec's `CrossNet` with `glideator_ml.xc.model.CrossNet`. The replacement preserves the full-rank equation and legacy state-dict parameter names/shapes.

No prediction semantics are intentionally changed in this reference model.

## Training contract

- strict targets: `max_points > threshold`;
- summed BCE across the eleven heads;
- optional adjacent-threshold monotonicity penalty;
- Adam optimizer and exponential LR decay;
- weather scaler fitted from 12:00 training features and reused at all three times;
- site scaler fitted from training rows only.

The stable comparison benchmark is `xc-temporal-2024-v1`, not the old random `is_validation` split.

## Serving implications

The output shape and target order match the current backend contract, but the generated `.pt` checkpoint is not a serving artifact. Production still consumes ONNX.

Promotion requires an explicit PyTorch/ONNX parity gate and a documented production artifact contract. Until then this model is an experiment/reference implementation only.
