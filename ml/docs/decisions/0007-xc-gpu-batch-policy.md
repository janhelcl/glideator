# 0007 — Use batch size 8192 for XC GPU experiments

Status: Accepted
Date: 2026-09-07

## Context

The migrated XC trainer inherited `batch_size: 2048` from a CPU-oriented workflow. The current experiment host uses an RTX 3090, so the batch size needed an empirical hardware operating point before architecture work.

A real forward/backward/Adam profile on 181,040 fit rows compared batch sizes 2,048 through 65,536. Throughput rose from about 59.7k samples/s at 2,048 to 69.1k at 8,192, then flattened; peak measured throughput was about 71.3k samples/s at 65,536. CUDA allocation was only about 0.17 GiB at 8,192 and remained below 1 GiB even at 65,536.

The larger batches therefore save very little wall time after 8,192 while sharply reducing optimizer updates per epoch: 23 at 8,192 versus only 3 at 65,536.

## Decision

Use `batch_size: 8192` as the default operating point for current XC architecture experiments on the RTX 3090.

Do not select the largest batch that fits. Prefer the smallest batch reaching at least 95% of measured peak throughput.

Because 8,192 is four times the previous batch size, normalize early-stopping patience by approximate optimizer-step budget. The current screening policy uses `patience: 40` instead of 10.

## Why

8,192 captures almost all available throughput while retaining materially more optimizer updates than larger batches. The profiler indicates the current training path is transfer-bound rather than memory- or compute-bound, but at roughly 2.6 seconds per estimated fit epoch the remaining input-pipeline optimization is not worth prioritizing before model architecture work.

## Consequences

- XC architecture comparisons use batch 8,192 unless an experiment explicitly studies optimization policy.
- Architecture and batch-size effects should not be changed simultaneously.
- Input transfer optimization is deferred.
- Re-profile if the GPU, dataset representation, data-loader path, precision mode, or model scale changes materially.

## Evidence

- MLflow batch-profile run: `dd1a6c9b73ce4b889fc270d43783ecfc`
- Report: `outputs/xc/gpu-batch-profile/batch_profile.json`
- RTX 3090 profile: 8,192 reached at least 95% of peak throughput with 23 optimizer steps/epoch.
