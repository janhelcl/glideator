from __future__ import annotations

import argparse
import json
import logging

from .config import load_config, require_sections

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glideator-ml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run a model experiment")
    run.add_argument("task", choices=["s2s", "xc"])
    run.add_argument("--config", required=True)

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Evaluate an existing production/reference artifact",
    )
    evaluate.add_argument("task", choices=["xc"])
    evaluate.add_argument("--config", required=True)

    compare = subparsers.add_parser(
        "compare",
        help="Compare a candidate with its promotion reference",
    )
    compare.add_argument("task", choices=["xc"])
    compare.add_argument("--config", required=True)

    benchmark = subparsers.add_parser(
        "benchmark",
        help="Run reference, candidate and promotion as one benchmark workflow",
    )
    benchmark.add_argument("task", choices=["xc"])
    benchmark.add_argument("--config", required=True, help="Candidate config")
    benchmark.add_argument("--reference-config", required=True)

    profile_batch = subparsers.add_parser(
        "profile-batch",
        help="Profile XC training throughput across GPU batch sizes",
    )
    profile_batch.add_argument("task", choices=["xc"])
    profile_batch.add_argument("--config", required=True)
    profile_batch.add_argument(
        "--batch-sizes",
        nargs="+",
        type=int,
        default=[2048, 4096, 8192, 16384, 32768, 65536],
    )
    profile_batch.add_argument("--warmup-steps", type=int, default=5)
    profile_batch.add_argument("--steps", type=int, default=20)
    profile_batch.add_argument(
        "--throughput-fraction",
        type=float,
        default=0.95,
        help="Recommend the smallest batch within this fraction of peak throughput",
    )

    backfill = subparsers.add_parser(
        "backfill",
        help="Backfill tracking from saved experiment artifacts",
    )
    backfill.add_argument("task", choices=["s2s", "xc"])
    backfill.add_argument("--config", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    if config["task"] != args.task:
        raise SystemExit(
            f"Config task {config['task']!r} does not match CLI task {args.task!r}"
        )

    exit_code = 0
    if args.command == "benchmark":
        require_sections(
            config, "data", "model", "evaluation", "artifact", "promotion", "tracking"
        )
        reference_config = load_config(args.reference_config)
        if reference_config["task"] != args.task:
            raise SystemExit(
                f"Reference config task {reference_config['task']!r} does not match "
                f"CLI task {args.task!r}"
            )
        require_sections(
            reference_config, "data", "evaluation", "reference", "artifact", "tracking"
        )
        from .xc.workflow import run_xc_benchmark_workflow

        report = run_xc_benchmark_workflow(config, reference_config)
        if not report["eligible"]:
            exit_code = 2
    elif args.command == "profile-batch":
        require_sections(config, "data", "model", "artifact")
        from .xc.performance import run_xc_batch_profile

        report = run_xc_batch_profile(
            config,
            batch_sizes=args.batch_sizes,
            warmup_steps=args.warmup_steps,
            measured_steps=args.steps,
            throughput_fraction=args.throughput_fraction,
        )
    elif args.command == "evaluate":
        require_sections(config, "data", "evaluation", "reference", "artifact", "tracking")
        from .xc.reference import run_xc_onnx_reference

        report = run_xc_onnx_reference(config)
    elif args.command == "compare":
        require_sections(config, "artifact", "promotion")
        from .xc.promotion import run_xc_promotion_check

        report = run_xc_promotion_check(config)
        if not report["eligible"]:
            exit_code = 2
    elif args.task == "s2s":
        require_sections(config, "data", "model", "evaluation", "artifact", "tracking")
        from .s2s.run import backfill_s2s_tracking, run_s2s

        report = (
            run_s2s(config)
            if args.command == "run"
            else backfill_s2s_tracking(config)
        )
    elif args.task == "xc":
        require_sections(config, "data", "model", "evaluation", "artifact", "tracking")
        from .xc.run import backfill_xc_tracking, run_xc

        report = (
            run_xc(config)
            if args.command == "run"
            else backfill_xc_tracking(config)
        )
    else:
        raise SystemExit(f"Unsupported command/task: {args.command}/{args.task}")

    print(json.dumps(report, indent=2, sort_keys=True))
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
